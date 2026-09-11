"""Backfill the dashboard index from existing local run artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping

from solution_runner.group_inventory_store import (
    GroupInventoryItem,
    GroupInventorySnapshot,
    GroupInventoryStore,
    GroupItemStageResult,
)
from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.grid_polygon.mcp_runtime import DEFAULT_MCP_URL, JsonRpcMcpGateway

from .initialization import GroupInitializer


def _json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _results(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict) and isinstance(payload.get("results"), list):
        return [item for item in payload["results"] if isinstance(item, dict)]
    return []


def _dry_status(value: Any) -> str:
    if value in {"prepared", "planned", "already_complete"}:
        return "ready"
    if value in {"blocked", "skipped"}:
        return "skipped"
    return "failed"


def _replay_stage_results(
    store: GroupInventoryStore,
    group_key: str,
    run_dirs: list[Path],
    problem_ids: set[str],
) -> None:
    for run_dir in sorted(run_dirs, key=lambda path: path.name):
        summary = _json(run_dir / "summary.json")
        is_apply = bool(summary.get("apply")) if isinstance(summary, dict) else False
        is_apply = is_apply or (run_dir / "apply-results.json").is_file()
        manifest = _json(run_dir / "prepared-manifest.json")
        if isinstance(manifest, dict):
            for record in manifest.get("records", []):
                if not isinstance(record, dict) or str(record.get("problem_id")) not in problem_ids:
                    continue
                message = record.get("message") or record.get("error")
                store.update_item_stage(GroupItemStageResult(
                    group_key=group_key,
                    problem_id=str(record["problem_id"]),
                    dry_run_status=_dry_status(record.get("status")),
                    error=" ".join(str(message).split())[:500] if message else None,
                ))
        if not is_apply:
            continue
        solution_file = (
            run_dir / "apply-results.json"
            if (run_dir / "apply-results.json").is_file()
            else run_dir / "solution-results.json"
        )
        for path, field in (
            (solution_file, "apply_status"),
            (run_dir / "helpers-results.json", "helpers_status"),
        ):
            for result in _results(_json(path)):
                problem_id = str(result.get("problem_id") or "")
                if problem_id not in problem_ids:
                    continue
                message = result.get("message") or result.get("error")
                store.update_item_stage(GroupItemStageResult(
                    group_key=group_key,
                    problem_id=problem_id,
                    **{field: str(result.get("status") or "unknown")},
                    error=" ".join(str(message).split())[:500] if message else None,
                ))


def backfill_local_runs(
    store: GroupInventoryStore,
    var_dir: Path,
    profiles: Mapping[str, Any],
) -> dict[str, int]:
    """Import known identities and outcomes without contacting MCP."""

    runs_by_group: dict[str, list[Path]] = {}
    for summary_path in var_dir.glob("**/runs/*/summary.json"):
        summary = _json(summary_path)
        group_key = str(summary.get("group_key") or "") if isinstance(summary, dict) else ""
        if group_key in profiles:
            runs_by_group.setdefault(group_key, []).append(summary_path.parent)

    groups = tasks = skipped_ready = 0
    for group_key, run_dirs in runs_by_group.items():
        current = store.get(group_key)
        if current is not None and current.status == "ready":
            _replay_stage_results(
                store, group_key, run_dirs, {item.problem_id for item in current.items}
            )
            skipped_ready += 1
            continue
        profile = profiles[group_key]
        records_by_problem: dict[str, dict[str, Any]] = {}
        source_group_id = str(profile.source_group_id)
        catalog_snapshot_id = str(profile.catalog_snapshot_id)
        for run_dir in sorted(run_dirs, key=lambda path: path.name):
            manifest = _json(run_dir / "prepared-manifest.json")
            if not isinstance(manifest, dict):
                continue
            source_group_id = str(manifest.get("source_group_id") or source_group_id)
            catalog_snapshot_id = str(manifest.get("catalog_snapshot_id") or catalog_snapshot_id)
            for record in manifest.get("records", []):
                if not isinstance(record, dict):
                    continue
                problem_id = str(record.get("problem_id") or "")
                source_problem_id = str(record.get("source_problem_id") or "")
                if problem_id and source_problem_id:
                    records_by_problem.setdefault(problem_id, dict(record))
                    records_by_problem[problem_id].update(record)
        if not records_by_problem:
            continue

        items = tuple(
            GroupInventoryItem(
                problem_id=problem_id,
                source_problem_id=str(record["source_problem_id"]),
                position=position,
                has_condition=False,
                has_solution=False,
                has_answer=False,
            )
            for position, (problem_id, record) in enumerate(records_by_problem.items())
        )
        store.replace(GroupInventorySnapshot(
            group_key=group_key,
            catalog_snapshot_id=catalog_snapshot_id,
            source_group_id=source_group_id,
            parent_problem_id=items[0].problem_id,
            parent_source_problem_id=items[0].source_problem_id,
            items=items,
        ))
        store.set_status(group_key, "partial", "Recovered from local runs; MCP inventory is incomplete")

        _replay_stage_results(store, group_key, run_dirs, set(records_by_problem))
        groups += 1
        tasks += len(items)
    return {"groups": groups, "tasks": tasks, "skipped_ready": skipped_ready}


def backfill_mcp_inventory(
    store: GroupInventoryStore,
    profiles: Mapping[str, Any],
    initializer: GroupInitializer,
    *,
    progress: Callable[[int, int, str, Mapping[str, Any]], None] | None = None,
) -> dict[str, int]:
    """Complete every non-ready inventory with bounded read-only MCP calls."""

    ready = failed = tasks = skipped_ready = 0
    pending = []
    for key in profiles:
        snapshot = store.get(key)
        if snapshot is None or snapshot.status != "ready":
            pending.append(key)
    skipped_ready = len(profiles) - len(pending)
    for index, group_key in enumerate(pending, 1):
        state = initializer.run_now(group_key)
        if state.get("status") == "ready":
            ready += 1
            tasks += int(state.get("total") or 0)
        else:
            failed += 1
        if progress:
            progress(index, len(pending), group_key, state)
    return {"ready": ready, "failed": failed, "tasks": tasks, "skipped_ready": skipped_ready}


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=root / "var/dashboard/dashboard.sqlite3")
    parser.add_argument("--var", type=Path, default=root / "var")
    parser.add_argument(
        "--mcp", action="store_true",
        help="complete incomplete inventories using read-only TeacherHelper MCP calls",
    )
    args = parser.parse_args(argv)
    store = GroupInventoryStore(args.db)
    profiles = all_group_profiles()
    report: dict[str, Any] = {"local": backfill_local_runs(store, args.var, profiles)}
    if args.mcp:
        api_key = os.environ.get("TEACHERHELPER_MCP_API_KEY", "").strip()
        if not api_key:
            parser.error("TEACHERHELPER_MCP_API_KEY is required with --mcp")
        initializer = GroupInitializer(
            profiles=profiles,
            inventory_store=store,
            gateway_factory=lambda: JsonRpcMcpGateway(
                url=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
                api_key=api_key,
                timeout_seconds=45,
            ),
        )
        report["mcp"] = backfill_mcp_inventory(
            store,
            profiles,
            initializer,
            progress=lambda index, total, key, state: print(
                f"[{index}/{total}] group {key}: {state.get('status')} "
                f"tasks={state.get('total', 0)}",
                flush=True,
            ),
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
