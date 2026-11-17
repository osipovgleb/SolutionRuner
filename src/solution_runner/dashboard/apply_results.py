"""Read and classify results from dashboard apply runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SUCCESS = {"applied", "already_complete"}


def _read_results(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        payload = payload.get("results", [])
    return (
        [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, list)
        else []
    )


def _latest_run(var_dir: Path, group_key: str) -> Path | None:
    matches: list[Path] = []
    for summary_path in var_dir.glob("**/runs/*/summary.json"):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(summary, dict) and str(summary.get("group_key")) == group_key:
            matches.append(summary_path.parent)
    return max(matches, key=lambda path: path.stat().st_mtime_ns) if matches else None


def _result_for(rows: list[dict[str, Any]], problem_id: str) -> dict[str, Any] | None:
    return next((row for row in rows if str(row.get("problem_id")) == problem_id), None)


def _label_dashboard_run(run_dir: Path, *, action: str, scope: str) -> None:
    summary_path = run_dir / "summary.json"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(summary, dict):
        return
    summary.update(dashboard_action=action, dashboard_scope=scope)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _stage_error(
    solution: Mapping[str, Any] | None,
    helper: Mapping[str, Any] | None,
    solution_status: str,
    helpers_status: str,
) -> str | None:
    if solution_status not in SUCCESS:
        return str(
            (solution or {}).get("error")
            or (solution or {}).get("message")
            or "MCP не записал решение"
        )
    if helpers_status not in SUCCESS:
        return str(
            (helper or {}).get("error")
            or (helper or {}).get("message")
            or "MCP не записал Helpers"
        )
    return None
