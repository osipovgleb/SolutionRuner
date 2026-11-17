"""Process polygon assets in ordered, isolated problem batches."""

from __future__ import annotations

import argparse
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

if __package__:
    from .mcp_polygon_client import McpClient, _safe_exception
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_models import (
        AssetCandidate,
        CandidateRejected,
        CandidateStale,
        McpCallError,
        PipelineError,
        _CandidateOutcome,
    )
    from .mcp_polygon_util import _chunks, _sha256_file
else:
    from mcp_polygon_client import McpClient, _safe_exception
    from mcp_polygon_events import EventLogger
    from mcp_polygon_models import (
        AssetCandidate,
        CandidateRejected,
        CandidateStale,
        McpCallError,
        PipelineError,
        _CandidateOutcome,
    )
    from mcp_polygon_util import _chunks, _sha256_file


def _apply_candidate(context, candidate, prepared):
    """Apply one prepared asset and capture its isolated outcome."""
    try:
        source_asset_id, cleanup = context.apply_prepared_asset(
            context.client,
            source_site_id=context.source_site_id,
            prepared=prepared,
            transfer_timeout_seconds=context.transfer_timeout_seconds,
            logger=context.logger,
        )
        context.logger.emit(
            "asset_replaced",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            transformation_target_id=prepared.transformation_target_id,
            source_asset_id=source_asset_id,
            output_sha256=prepared.output_sha256,
            alt_text=prepared.alt_text,
            cleanup=cleanup,
        )
        return _CandidateOutcome(
            candidate,
            "replaced",
            "apply",
            prepared=prepared,
            source_asset_id=source_asset_id,
            cleanup=cleanup,
        )
    except CandidateStale as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_stale",
            level="warning",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="apply",
            reason=reason,
        )
        return _CandidateOutcome(
            candidate,
            "stale",
            "apply",
            prepared=prepared,
            error=reason,
        )
    except (McpCallError, httpx.HTTPError, OSError, PipelineError) as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_error",
            level="error",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="apply",
            reason=reason,
        )
        return _CandidateOutcome(
            candidate,
            "error",
            "apply",
            prepared=prepared,
            error=reason,
        )


def _process_candidate(
    context: Any,
    candidate: AssetCandidate,
) -> _CandidateOutcome:
    """Prepare and optionally apply one asset as an isolated worker chain."""

    try:
        prepared = context.prepare_candidate(
            context.client,
            candidate=candidate,
            converter=context.converter,
            converter_fingerprint=context.converter_fingerprint,
            template_path=context.template_path,
            run_dir=context.run_dir,
            transfer_timeout_seconds=context.transfer_timeout_seconds,
            logger=context.logger,
        )
        context.determinism_gate.verify(prepared, context.logger)
        context.logger.emit(
            "asset_prepared",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            input_sha256=prepared.input_sha256,
            output_sha256=prepared.output_sha256,
            alt_text=prepared.alt_text,
            validation=prepared.validation,
            svg_path=str(prepared.svg_path),
        )
    except CandidateStale as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_stale",
            level="warning",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="prepare",
            reason=reason,
        )
        return _CandidateOutcome(candidate, "stale", "prepare", error=reason)
    except CandidateRejected as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_rejected",
            level="warning",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            reason=reason,
        )
        return _CandidateOutcome(candidate, "rejected", "prepare", error=reason)
    except (McpCallError, httpx.HTTPError, OSError) as exc:
        reason = _safe_exception(exc)
        context.logger.emit(
            "asset_error",
            level="error",
            theme=candidate.theme_title,
            group_key=candidate.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            stage="prepare",
            reason=reason,
        )
        return _CandidateOutcome(candidate, "error", "prepare", error=reason)

    if not context.apply:
        return _CandidateOutcome(
            candidate,
            "dry_run",
            "prepare",
            prepared=prepared,
        )
    return _apply_candidate(context, candidate, prepared)


def _process_problem_unit(
    context: Any,
    candidates: tuple[AssetCandidate, ...],
) -> tuple[_CandidateOutcome, ...]:
    """Process every asset of one problem sequentially inside one worker."""

    return tuple(_process_candidate(context, candidate) for candidate in candidates)


def _problem_units(
    candidates: Sequence[AssetCandidate],
) -> tuple[tuple[AssetCandidate, ...], ...]:
    """Group ordered asset candidates by their source problem identity."""

    by_problem: dict[str, list[AssetCandidate]] = {}
    for candidate in candidates:
        by_problem.setdefault(candidate.problem_id, []).append(candidate)
    return tuple(tuple(values) for values in by_problem.values())


def _problem_batches(
    candidates: Sequence[AssetCandidate], batch_size: int
) -> Iterator[list[AssetCandidate]]:
    """Yield batches containing all assets for at most *batch_size* problems."""

    by_problem: dict[str, list[AssetCandidate]] = {}
    order: list[str] = []
    for candidate in candidates:
        if candidate.problem_id not in by_problem:
            order.append(candidate.problem_id)
            by_problem[candidate.problem_id] = []
        by_problem[candidate.problem_id].append(candidate)
    for problem_chunk in _chunks(order, batch_size):
        yield [
            candidate
            for problem_id in problem_chunk
            for candidate in by_problem[problem_id]
        ]


def _assert_locked_inputs(
    *,
    converter_path: Path,
    converter_fingerprint: str,
    template_path: Path,
    template_fingerprint: str,
) -> None:
    """Stop if converter code or its SVG template changes during the run."""

    if _sha256_file(converter_path) != converter_fingerprint:
        raise PipelineError("converter file changed during the run")
    if _sha256_file(template_path) != template_fingerprint:
        raise PipelineError("SVG template changed during the run")


def _validate_write_batch_policy(args: argparse.Namespace) -> None:
    """Require ten-task checkpoints and a bounded sliding worker window."""

    if args.batch_size != 10:
        raise PipelineError("write mode requires batches of 10")
    if not 1 <= getattr(args, "max_workers", 10) <= 10:
        raise PipelineError("write mode requires between 1 and 10 workers")


def account_outcomes(totals, outcomes, consecutive_asset_errors):
    """Accumulate one ordered parallel checkpoint's asset outcomes."""
    prepared_count = 0
    replaced_count = 0
    for outcome in outcomes:
        totals["assets_attempted"] += 1
        if outcome.prepared is not None:
            totals["assets_prepared"] += 1
            prepared_count += 1
        counter_key = {
            "replaced": "assets_replaced",
            "dry_run": "assets_dry_run",
            "stale": "assets_stale",
            "rejected": "assets_rejected",
            "error": "asset_errors",
        }.get(outcome.status)
        if counter_key is None:
            continue
        totals[counter_key] += 1
        if outcome.status == "replaced":
            replaced_count += 1
        consecutive_asset_errors = (
            consecutive_asset_errors + 1 if outcome.status == "error" else 0
        )
    return prepared_count, replaced_count, consecutive_asset_errors


@dataclass(frozen=True)
class _ProcessingContext:
    """Share immutable candidate dependencies across bounded worker threads."""

    client: McpClient
    source_site_id: str
    converter: Any
    converter_fingerprint: str
    template_path: Path
    run_dir: Path
    transfer_timeout_seconds: float
    logger: EventLogger
    apply: bool
    determinism_gate: Any
    prepare_candidate: Any
    apply_prepared_asset: Any
