"""Execute guarded rollback batches for polygon transformations."""

from __future__ import annotations

import argparse
import time
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx

if __package__:
    from .mcp_polygon_client import McpClient, _safe_exception
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_models import (
        GroupScope,
        McpCallError,
        PipelineError,
        RollbackCandidate,
        ThemeScope,
    )
    from .mcp_polygon_resume import _rollback_inventory_from_run
    from .mcp_polygon_util import _atomic_write_json, _chunks
else:
    from mcp_polygon_client import McpClient, _safe_exception
    from mcp_polygon_events import EventLogger
    from mcp_polygon_models import (
        GroupScope,
        McpCallError,
        PipelineError,
        RollbackCandidate,
        ThemeScope,
    )
    from mcp_polygon_resume import _rollback_inventory_from_run
    from mcp_polygon_util import _atomic_write_json, _chunks


def _rollback_batches(
    candidates: Sequence[RollbackCandidate], batch_size: int
) -> Iterator[list[RollbackCandidate]]:
    """Yield rollback batches containing at most *batch_size* problems."""

    by_problem: dict[str, list[RollbackCandidate]] = {}
    order: list[str] = []
    for item in candidates:
        problem_id = item.candidate.problem_id
        if problem_id not in by_problem:
            order.append(problem_id)
            by_problem[problem_id] = []
        by_problem[problem_id].append(item)
    for problem_chunk in _chunks(order, batch_size):
        yield [item for problem_id in problem_chunk for item in by_problem[problem_id]]


def _rollback_error_is_stale(exc: BaseException) -> bool:
    """Return whether rollback safely refused an absent or newer value."""

    reason = _safe_exception(exc).lower()
    return (
        "current problem transformation not found" in reason
        or "does not match expected_source_asset_id" in reason
    )


@dataclass(frozen=True)
class _RollbackContext:
    client: McpClient
    totals: Counter[str]
    args: argparse.Namespace
    logger: EventLogger


def _rollback_asset(context, theme, group, item, consecutive_asset_errors):
    client, totals, args, logger = (
        context.client,
        context.totals,
        context.args,
        context.logger,
    )
    candidate = item.candidate
    totals["rollback_attempted"] += 1
    succeeded = False
    try:
        result = client.call(
            "delete_problem_transformation",
            {
                "problem_id": candidate.problem_id,
                "transformation_target_id": (item.transformation_target_id),
                "expected_source_asset_id": item.source_asset_id,
            },
            attempts=1,
        )
        if (
            str(result.get("problem_id") or "") != candidate.problem_id
            or str(result.get("deleted_transformation_target_id") or "")
            != item.transformation_target_id
        ):
            raise PipelineError("rollback response does not match requested target")
        succeeded = True
        totals["assets_rolled_back"] += 1
        consecutive_asset_errors = 0
        logger.emit(
            "asset_rolled_back",
            theme=theme.title,
            group_key=group.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            transformation_target_id=item.transformation_target_id,
            source_asset_id=item.source_asset_id,
            output_sha256=item.output_sha256,
            reopened_stages=result.get("reopened_stages", []),
        )
    except (
        McpCallError,
        httpx.HTTPError,
        OSError,
        PipelineError,
    ) as exc:
        if _rollback_error_is_stale(exc):
            totals["rollback_stale"] += 1
            consecutive_asset_errors = 0
            logger.emit(
                "rollback_stale",
                level="warning",
                theme=theme.title,
                group_key=group.group_key,
                source_problem_id=candidate.source_problem_id,
                problem_id=candidate.problem_id,
                asset_key=candidate.asset_key,
                reason=_safe_exception(exc),
            )
            return 0, consecutive_asset_errors
        totals["asset_errors"] += 1
        consecutive_asset_errors += 1
        logger.emit(
            "asset_error",
            level="error",
            theme=theme.title,
            group_key=group.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="rollback",
            reason=_safe_exception(exc),
        )
        if args.max_asset_errors and consecutive_asset_errors >= args.max_asset_errors:
            raise PipelineError(
                "maximum consecutive asset error count reached"
            ) from exc
    return int(succeeded), consecutive_asset_errors


def _record_rollback_batch(context, run_dir, theme, group, counts, batch):
    logger, totals = context.logger, context.totals
    batches_seen, global_tasks_seen = counts
    problem_order, batch_candidates, rolled_back_in_batch = batch
    logger.emit(
        "batch_complete",
        theme=theme.title,
        group_key=group.group_key,
        batch=batches_seen,
        tasks=len(problem_order),
        assets=len(batch_candidates),
        rolled_back=rolled_back_in_batch,
    )
    _atomic_write_json(
        run_dir / "progress.json",
        {
            "at": datetime.now(UTC).isoformat(),
            "mode": "rollback",
            "last_theme": theme.title,
            "last_source_group_id": group.source_group_id,
            "last_group_key": group.group_key,
            "batches_seen": batches_seen,
            "tasks_seen": global_tasks_seen,
            "totals": dict(sorted(totals.items())),
        },
    )


def _open_rollback_group(logger, theme, group, candidates):
    group_task_count = len({item.candidate.problem_id for item in candidates})
    logger.emit(
        "group_transition",
        theme=theme.title,
        group_key=group.group_key,
        source_group_id=group.source_group_id,
    )
    logger.emit(
        "group_opened",
        theme=theme.title,
        group_key=group.group_key,
        source_group_id=group.source_group_id,
        tasks=group_task_count,
        assets=len(candidates),
    )


def _execute_rollback(
    client: McpClient,
    *,
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    rollback_by_group: dict[str, list[RollbackCandidate]],
    totals: Counter[str],
    args: argparse.Namespace,
    run_dir: Path,
    logger: EventLogger,
) -> tuple[int, int, bool]:
    """Delete exact historical transformations in bounded sequential batches."""

    global_tasks_seen = 0
    batches_seen = 0
    consecutive_asset_errors = 0
    stop_requested = False
    for theme, groups in scope:
        if stop_requested:
            break
        logger.emit(
            "theme_start",
            theme=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            groups=len(groups),
        )
        for group in groups:
            if stop_requested:
                break
            candidates = rollback_by_group[group.source_group_id]
            if not candidates:
                continue
            _open_rollback_group(logger, theme, group, candidates)
            for local_batch_index, batch_candidates in enumerate(
                _rollback_batches(candidates, args.batch_size), start=1
            ):
                problem_order = list(
                    dict.fromkeys(
                        item.candidate.problem_id for item in batch_candidates
                    )
                )
                if args.max_tasks is not None:
                    remaining = args.max_tasks - global_tasks_seen
                    if remaining <= 0:
                        stop_requested = True
                        break
                    allowed_problem_ids = set(problem_order[:remaining])
                    batch_candidates = [
                        item
                        for item in batch_candidates
                        if item.candidate.problem_id in allowed_problem_ids
                    ]
                    problem_order = problem_order[:remaining]
                global_tasks_seen += len(problem_order)
                batches_seen += 1
                logger.emit(
                    "batch_start",
                    theme=theme.title,
                    group_key=group.group_key,
                    batch=batches_seen,
                    group_batch=local_batch_index,
                    tasks=len(problem_order),
                    assets=len(batch_candidates),
                    source_problem_ids=[
                        item.candidate.source_problem_id for item in batch_candidates
                    ],
                )
                rolled_back_in_batch = 0
                rollback_context = _RollbackContext(client, totals, args, logger)
                for item in batch_candidates:
                    rolled_back, consecutive_asset_errors = _rollback_asset(
                        rollback_context, theme, group, item, consecutive_asset_errors
                    )
                    rolled_back_in_batch += rolled_back
                _record_rollback_batch(
                    rollback_context,
                    run_dir,
                    theme,
                    group,
                    (batches_seen, global_tasks_seen),
                    (problem_order, batch_candidates, rolled_back_in_batch),
                )
                if batch_candidates:
                    logger.emit(
                        "batch_pause",
                        theme=theme.title,
                        group_key=group.group_key,
                        batch=batches_seen,
                        seconds=args.batch_pause_seconds,
                    )
                    time.sleep(args.batch_pause_seconds)
                if (
                    args.stop_after_batches is not None
                    and batches_seen >= args.stop_after_batches
                ):
                    stop_requested = True
                if args.max_tasks is not None and global_tasks_seen >= args.max_tasks:
                    stop_requested = True
        logger.emit("theme_complete", theme=theme.title)
    return global_tasks_seen, batches_seen, stop_requested


@dataclass(frozen=True)
class RollbackRun:
    args: argparse.Namespace
    run_dir: Path
    logger: EventLogger
    user_id: str
    source_site_id: str
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]]


def finish_rollback_run(client: McpClient, run: RollbackRun) -> int:
    """Execute rollback and persist its final summary."""
    args, run_dir, logger = run.args, run.run_dir, run.logger
    user_id, source_site_id, scope = run.user_id, run.source_site_id, run.scope
    rollback_by_group, totals = _rollback_inventory_from_run(
        source_run_dir=args.resume_from_run,
        run_dir=run_dir,
        catalog_snapshot_id=args.catalog_snapshot_id,
        source_site_id=source_site_id,
        category_key=args.category_key,
        theme_titles=args.theme_titles,
        scope=scope,
        logger=logger,
    )
    global_tasks_seen, batches_seen, stop_requested = _execute_rollback(
        client,
        scope=scope,
        rollback_by_group=rollback_by_group,
        totals=totals,
        args=args,
        run_dir=run_dir,
        logger=logger,
    )
    status = "limited_complete" if stop_requested else "completed"
    if totals.get("rollback_stale"):
        status += "_with_skips"
    if totals.get("asset_errors"):
        status += "_with_errors"
    summary = {
        "at": datetime.now(UTC).isoformat(),
        "status": status,
        "mode": args.mode,
        "run_dir": str(run_dir),
        "source_run_dir": str(args.resume_from_run.resolve()),
        "user_id": user_id,
        "catalog_snapshot_id": args.catalog_snapshot_id,
        "source_site_id": source_site_id,
        "batches_seen": batches_seen,
        "tasks_seen": global_tasks_seen,
        "totals": dict(sorted(totals.items())),
    }
    _atomic_write_json(run_dir / "summary.json", summary)
    logger.emit("run_complete", status=status, **summary["totals"])
    return 0 if not totals.get("asset_errors") else 2
