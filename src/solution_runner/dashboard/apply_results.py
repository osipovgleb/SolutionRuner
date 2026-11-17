"""Read and classify results from dashboard apply runs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from solution_runner.group_inventory_store import GroupItemStageResult

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


def _record_helpers(inventory_store, group_key, problem_ids, helpers):
    completed = True
    last_error = "Helpers не выполнены"
    for problem_id in problem_ids:
        helper = helpers.get(problem_id)
        helpers_status = str(helper.get("status") or "failed") if helper else "failed"
        error = (
            None
            if helpers_status in SUCCESS
            else str(
                (helper or {}).get("error")
                or (helper or {}).get("message")
                or "MCP не записал Helpers"
            )
        )
        completed = completed and error is None
        if error:
            last_error = " ".join(error.split())[:300]
        inventory_store.update_item_stage(
            GroupItemStageResult(
                group_key=group_key,
                problem_id=problem_id,
                helpers_status=helpers_status,
                error=" ".join(error.split())[:500] if error else None,
            )
        )
    return completed, last_error


def _record_group_results(inventory_store, group_key, rows, solutions, helpers):
    last_error = "Не все задачи удалось записать и проверить."
    inventory_store.clear_apply_results(group_key)
    terminal_statuses: list[str] = []
    for row in rows:
        problem_id = str(row["problem_id"])
        solution = solutions.get(problem_id)
        helper = helpers.get(problem_id)
        solution_status = (
            str(solution.get("status") or "failed") if solution else "failed"
        )
        helpers_status = str(helper.get("status") or "failed") if helper else "failed"
        error = _stage_error(solution, helper, solution_status, helpers_status)
        if error:
            last_error = " ".join(error.split())[:300]
        inventory_store.update_item_stage(
            GroupItemStageResult(
                group_key=group_key,
                problem_id=problem_id,
                apply_status=solution_status,
                helpers_status=helpers_status,
                error=" ".join(error.split())[:500] if error else None,
            )
        )
        terminal_statuses.extend((solution_status, helpers_status))
    completed = all(status in SUCCESS for status in terminal_statuses)
    return completed, last_error


def _record_problem_result(inventory_store, group_key, problem_id, run_dir):
    solution = _result_for(_read_results(run_dir / "solution-results.json"), problem_id)
    helpers = _result_for(_read_results(run_dir / "helpers-results.json"), problem_id)
    if solution is None:
        raise RuntimeError("launcher produced no result for the selected problem")
    solution_status = str(solution.get("status") or "failed")
    helpers_status = str(helpers.get("status") or "failed") if helpers else "failed"
    error = _stage_error(solution, helpers, solution_status, helpers_status)
    inventory_store.update_item_stage(
        GroupItemStageResult(
            group_key=group_key,
            problem_id=problem_id,
            apply_status=solution_status,
            helpers_status=helpers_status,
            error=" ".join(str(error).split())[:500] if error else None,
        )
    )
    return solution_status, helpers_status, error
