"""Apply one previously verified dashboard problem through the shared launcher."""

from __future__ import annotations

from concurrent.futures import Executor, ThreadPoolExecutor
from datetime import UTC, datetime
import json
from pathlib import Path
from threading import Lock
import time
from typing import Any, Callable, Mapping

from solution_runner.group_inventory_store import GroupInventoryStore, GroupItemStageResult
from solution_runner.launcher import main as launcher_main


SUCCESS = {"applied", "already_complete"}


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _execute(argv: list[str]) -> int:
    return launcher_main(argv)


def _read_results(path: Path) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, dict):
        payload = payload.get("results", [])
    return [item for item in payload if isinstance(item, dict)] if isinstance(payload, list) else []


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
        return str((solution or {}).get("error") or (solution or {}).get("message") or "MCP не записал решение")
    if helpers_status not in SUCCESS:
        return str((helper or {}).get("error") or (helper or {}).get("message") or "MCP не записал Helpers")
    return None


class ApplyManager:
    """Serialize explicit problem or whole-group writes and keep local state."""

    def __init__(
        self,
        *,
        var_dir: Path,
        profiles: Mapping[str, Any],
        inventory_store: GroupInventoryStore,
        store: Any | None = None,
        executor: Callable[[list[str]], int] = _execute,
        sleeper: Callable[[float], None] = time.sleep,
        retry_delays: tuple[int, ...] = (5, 10, 15),
        background_executor: Executor | None = None,
    ) -> None:
        self.var_dir = var_dir
        self.profiles = profiles
        self.inventory_store = inventory_store
        self.store = store
        self.executor_fn = executor
        self.sleeper = sleeper
        self.retry_delays = retry_delays
        self.state_dir = var_dir / "dashboard/applies"
        self.executor = background_executor or ThreadPoolExecutor(max_workers=1, thread_name_prefix="dashboard-apply")
        self.lock = Lock()

    def _path(self, group_key: str) -> Path:
        return self.state_dir / f"{group_key}.json"

    def _write(self, state: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(state)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        target = self._path(str(payload["group_key"]))
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(target)
        return payload

    def get(self, group_key: str) -> dict[str, Any] | None:
        try:
            payload = json.loads(self._path(group_key).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def _verified_row(self, group_key: str, problem_id: str) -> dict[str, object]:
        if group_key not in self.profiles:
            raise KeyError(group_key)
        row = next(
            (item for item in self.inventory_store.list_items(group_key)
             if str(item["problem_id"]) == problem_id),
            None,
        )
        if row is None:
            raise ValueError("problem does not belong to the initialized group")
        if row.get("dry_run_status") != "ready" and not row.get("error"):
            raise ValueError("problem requires a successful dry-run before apply")
        return row

    def _verified_group(self, group_key: str) -> list[dict[str, object]]:
        if group_key not in self.profiles:
            raise KeyError(group_key)
        rows = self.inventory_store.list_items(group_key)
        if not rows:
            raise ValueError("initialized group has no tasks")
        group = self.store.get_group(group_key) if self.store is not None else None
        if not group or group.get("full_dry_run_status") != "ready":
            raise ValueError("group requires a successful full-group dry-run before apply")
        return rows

    def start(self, group_key: str, problem_id: str) -> dict[str, Any]:
        self._verified_row(group_key, problem_id)
        with self.lock:
            current = self.get(group_key)
            if current and current.get("status") in {"queued", "running", "retry_wait"}:
                raise RuntimeError("apply already active")
            state = self._write({
                "group_key": group_key,
                "problem_id": problem_id,
                "scope": "problem",
                "status": "queued",
                "queued_at": _now(),
            })
            self.executor.submit(self.run_now, group_key, problem_id)
            return state

    def start_group(self, group_key: str) -> dict[str, Any]:
        self._verified_group(group_key)
        with self.lock:
            current = self.get(group_key)
            if current and current.get("status") in {"queued", "running", "retry_wait"}:
                raise RuntimeError("apply already active")
            state = self._write({
                "group_key": group_key,
                "scope": "group",
                "status": "queued",
                "queued_at": _now(),
            })
            self.executor.submit(self.run_group_now, group_key)
            return state

    def start_helpers(self, group_key: str, problem_id: str | None = None) -> dict[str, Any]:
        rows = self.inventory_store.list_items(group_key)
        if group_key not in self.profiles:
            raise KeyError(group_key)
        if problem_id:
            rows = [row for row in rows if str(row["problem_id"]) == problem_id]
            if not rows:
                raise ValueError("problem does not belong to the initialized group")
        rows = [
            row for row in rows
            if row.get("helpers_status") not in SUCCESS
            and (row.get("has_solution") or row.get("apply_status") in SUCCESS)
        ]
        if not rows:
            raise ValueError("no tasks require Helpers")
        problem_ids = tuple(str(row["problem_id"]) for row in rows)
        with self.lock:
            current = self.get(group_key)
            if current and current.get("status") in {"queued", "running", "retry_wait"}:
                raise RuntimeError("apply already active")
            state = self._write({
                "group_key": group_key,
                "problem_id": problem_id,
                "scope": "problem" if problem_id else "group",
                "stage": "helpers",
                "status": "queued",
                "queued_at": _now(),
            })
            self.executor.submit(self.run_helpers_now, group_key, problem_ids, state["scope"])
            return state

    def run_helpers_now(
        self,
        group_key: str,
        problem_ids: tuple[str, ...],
        scope: str | None = None,
    ) -> dict[str, Any]:
        profile = self.profiles[group_key]
        scope = scope or ("problem" if len(problem_ids) == 1 else "group")
        state: dict[str, Any] = {
            "group_key": group_key,
            "problem_id": problem_ids[0] if len(problem_ids) == 1 else None,
            "scope": scope,
            "stage": "helpers",
            "status": "running",
            "started_at": _now(),
        }
        self._write(state)
        argv = [
            "--group", str(profile.group_key),
            "--confirm-catalog", str(profile.catalog_snapshot_id),
            "--inventory-db", str(self.inventory_store.path),
            "--max-workers", "1" if len(problem_ids) == 1 else "5",
            "--apply",
            "--helpers-from-existing-solution",
        ]
        for problem_id in problem_ids:
            argv.extend(("--only-problem-id", problem_id))
        try:
            return_code = self.executor_fn(argv)
            if return_code:
                raise RuntimeError(f"launcher exited with status {return_code}")
            run_dir = _latest_run(self.var_dir, group_key)
            if run_dir is None:
                raise RuntimeError("launcher produced no run report")
            _label_dashboard_run(run_dir, action="helpers", scope=scope)
            helpers = {
                str(result.get("problem_id")): result
                for result in _read_results(run_dir / "helpers-results.json")
                if result.get("problem_id")
            }
            completed = True
            last_error = "Helpers не выполнены"
            for problem_id in problem_ids:
                helper = helpers.get(problem_id)
                helpers_status = str(helper.get("status") or "failed") if helper else "failed"
                error = None if helpers_status in SUCCESS else str(
                    (helper or {}).get("error") or (helper or {}).get("message") or "MCP не записал Helpers"
                )
                completed = completed and error is None
                if error:
                    last_error = " ".join(error.split())[:300]
                self.inventory_store.update_item_stage(GroupItemStageResult(
                    group_key=group_key,
                    problem_id=problem_id,
                    helpers_status=helpers_status,
                    error=" ".join(error.split())[:500] if error else None,
                ))
            items = self.inventory_store.list_items(group_key)
            if self.store is not None:
                self.store.reconcile_problem_counts(group_key, items)
            if completed:
                state.update(status="completed", completed_at=_now())
                if self.store is not None and all(
                    item.get("apply_status") in SUCCESS and item.get("helpers_status") in SUCCESS
                    for item in items
                ):
                    self.store.update_group(group_key, {"column": "done"})
            else:
                state.update(status="failed", completed_at=_now(), error=last_error)
                if self.store is not None:
                    self.store.update_group(group_key, {"column": "issues"})
            return self._write(state)
        except Exception as exc:  # noqa: BLE001 - persist an isolated dashboard operation.
            state.update(status="failed", completed_at=_now(), error=" ".join(str(exc).split())[:300])
            if self.store is not None:
                self.store.update_group(group_key, {"column": "issues"})
            return self._write(state)

    def run_now(self, group_key: str, problem_id: str) -> dict[str, Any]:
        self._verified_row(group_key, problem_id)
        profile = self.profiles[group_key]
        state: dict[str, Any] = {
            "group_key": group_key,
            "problem_id": problem_id,
            "scope": "problem",
            "status": "running",
            "started_at": _now(),
        }
        self._write(state)
        argv = [
            "--group", str(profile.group_key),
            "--confirm-catalog", str(profile.catalog_snapshot_id),
            "--inventory-db", str(self.inventory_store.path),
            "--max-workers", "1",
            "--apply",
            "--only-problem-id", problem_id,
        ]
        try:
            return_code = self.executor_fn(argv)
            if return_code:
                raise RuntimeError(f"launcher exited with status {return_code}")
            run_dir = _latest_run(self.var_dir, group_key)
            if run_dir is None:
                raise RuntimeError("launcher produced no run report")
            solution = _result_for(_read_results(run_dir / "solution-results.json"), problem_id)
            helpers = _result_for(_read_results(run_dir / "helpers-results.json"), problem_id)
            if solution is None:
                raise RuntimeError("launcher produced no result for the selected problem")
            solution_status = str(solution.get("status") or "failed")
            helpers_status = str(helpers.get("status") or "failed") if helpers else "failed"
            error = _stage_error(solution, helpers, solution_status, helpers_status)
            self.inventory_store.update_item_stage(GroupItemStageResult(
                group_key=group_key,
                problem_id=problem_id,
                apply_status=solution_status,
                helpers_status=helpers_status,
                error=" ".join(str(error).split())[:500] if error else None,
            ))
            items = self.inventory_store.list_items(group_key)
            if self.store is not None:
                self.store.reconcile_problem_counts(group_key, items)
            if solution_status in SUCCESS and helpers_status in SUCCESS:
                state.update(status="completed", completed_at=_now())
                if self.store is not None and all(
                    item.get("apply_status") in SUCCESS
                    and item.get("helpers_status") in SUCCESS
                    for item in items
                ):
                    self.store.update_group(group_key, {"column": "done"})
            elif "failed" in {solution_status, helpers_status}:
                state.update(status="failed", completed_at=_now(), error=str(error or "MCP write or readback failed"))
                if self.store is not None:
                    self.store.update_group(group_key, {"column": "issues"})
            else:
                state.update(status="skipped", completed_at=_now(), message=str(error or "Задача пропущена."))
            return self._write(state)
        except Exception as exc:  # noqa: BLE001 - persist an isolated dashboard operation.
            state.update(
                status="failed",
                completed_at=_now(),
                error=" ".join(str(exc).split())[:300],
            )
            if self.store is not None:
                self.store.update_group(group_key, {"column": "issues"})
            return self._write(state)

    def run_group_now(self, group_key: str) -> dict[str, Any]:
        rows = self._verified_group(group_key)
        profile = self.profiles[group_key]
        state: dict[str, Any] = {
            "group_key": group_key,
            "scope": "group",
            "status": "running",
            "started_at": _now(),
        }
        self._write(state)
        if self.store is not None:
            self.store.update_group(group_key, {"agent_status": None, "agent_summary": None})
        argv = [
            "--group", str(profile.group_key),
            "--confirm-catalog", str(profile.catalog_snapshot_id),
            "--inventory-db", str(self.inventory_store.path),
            "--max-workers", "5",
            "--apply",
        ]
        delays: tuple[int | None, ...] = (*self.retry_delays, None)
        last_error = "Не все задачи удалось записать и проверить."
        for attempt, delay in enumerate(delays, start=1):
            try:
                return_code = self.executor_fn(argv)
                if return_code:
                    raise RuntimeError(f"launcher exited with status {return_code}")
                run_dir = _latest_run(self.var_dir, group_key)
                if run_dir is None:
                    raise RuntimeError("launcher produced no run report")
                solutions = {
                    str(result.get("problem_id")): result
                    for result in _read_results(run_dir / "solution-results.json")
                    if result.get("problem_id")
                }
                helpers = {
                    str(result.get("problem_id")): result
                    for result in _read_results(run_dir / "helpers-results.json")
                    if result.get("problem_id")
                }
                self.inventory_store.clear_apply_results(group_key)
                terminal_statuses: list[str] = []
                for row in rows:
                    problem_id = str(row["problem_id"])
                    solution = solutions.get(problem_id)
                    helper = helpers.get(problem_id)
                    solution_status = str(solution.get("status") or "failed") if solution else "failed"
                    helpers_status = str(helper.get("status") or "failed") if helper else "failed"
                    error = _stage_error(solution, helper, solution_status, helpers_status)
                    if error:
                        last_error = " ".join(error.split())[:300]
                    self.inventory_store.update_item_stage(GroupItemStageResult(
                        group_key=group_key,
                        problem_id=problem_id,
                        apply_status=solution_status,
                        helpers_status=helpers_status,
                        error=" ".join(error.split())[:500] if error else None,
                    ))
                    terminal_statuses.extend((solution_status, helpers_status))
                completed = all(status in SUCCESS for status in terminal_statuses)
            except Exception as exc:  # noqa: BLE001 - one retry owns its current error.
                completed = False
                last_error = " ".join(str(exc).split())[:300]
            items = self.inventory_store.list_items(group_key)
            if self.store is not None:
                self.store.reconcile_problem_counts(group_key, items)
            if completed:
                state.update(status="completed", attempt=attempt, completed_at=_now())
                state.pop("retry_in_seconds", None)
                state.pop("error", None)
                if self.store is not None:
                    self.store.update_group(group_key, {
                        "column": "done",
                        "agent_status": None,
                        "agent_summary": None,
                    })
                return self._write(state)
            if self.store is not None:
                self.store.update_group(group_key, {"column": "issues"})
            if delay is None:
                break
            state.update(
                status="retry_wait",
                attempt=attempt,
                retry_in_seconds=delay,
                error=last_error,
            )
            self._write(state)
            self.sleeper(delay)
            state.update(status="running", attempt=attempt + 1)
            state.pop("retry_in_seconds", None)
            self._write(state)
        state.update(status="failed", attempt=len(delays), completed_at=_now(), error=last_error)
        state.pop("retry_in_seconds", None)
        return self._write(state)
