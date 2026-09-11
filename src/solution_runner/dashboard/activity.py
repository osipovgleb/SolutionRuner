"""Read local run history and unresolved task problems for one group."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from solution_runner.group_inventory_store import GroupInventoryStore


def _json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _started_at(run_name: str) -> str | None:
    try:
        value = datetime.strptime(run_name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None
    return value.isoformat()


def load_group_activity(
    var_dir: Path,
    group_key: str,
    inventory_store: GroupInventoryStore | None,
) -> dict[str, Any]:
    runs = []
    for summary_path in var_dir.glob("**/runs/*/summary.json"):
        summary = _json(summary_path)
        if summary is None or str(summary.get("group_key")) != group_key:
            continue
        run_name = summary_path.parent.name
        is_apply = bool(summary.get("apply")) or (summary_path.parent / "apply-results.json").is_file()
        runs.append({
            "run_name": run_name,
            "started_at": _started_at(run_name),
            "kind": "apply" if is_apply else "dry-run",
            "scope": "problem" if summary.get("targeted") else "group",
            "status": str(summary.get("status") or "unknown"),
            "targets": int(summary.get("targets") or 0),
            "prepared": int(summary.get("prepared") or 0),
            "failed": int(summary.get("failed_stage_results") or 0),
        })
    runs.sort(key=lambda run: run["run_name"], reverse=True)

    problems = []
    if inventory_store is not None:
        for row in inventory_store.list_items(group_key):
            if not row.get("error") and not any(
                row.get(field) in {"failed", "blocked"}
                for field in ("apply_status", "helpers_status")
            ):
                continue
            problems.append({
                "problem_id": row["problem_id"],
                "source_problem_id": row["source_problem_id"],
                "apply_status": row.get("apply_status"),
                "helpers_status": row.get("helpers_status"),
                "error": row.get("error"),
            })
    return {"latest": runs[0] if runs else None, "runs": runs, "problems": problems}
