"""Apply one previously verified dashboard problem through the shared launcher."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import Executor, ThreadPoolExecutor
from pathlib import Path
from threading import Lock
from typing import Any

from solution_runner.group_inventory_store import GroupInventoryStore

from .apply_results import (
    SUCCESS,
    _label_dashboard_run,
    _latest_run,
    _read_results,
    _record_group_results,
    _record_helpers,
    _record_problem_result,
)
from .apply_state import read_apply_state, write_apply_state
from .apply_validation import helper_targets, verified_group, verified_row
from .process_logs import run_solution_launcher as _execute
from .store_common import _now


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
        background_executor: Executor | None = None,
    ) -> None:
        self.var_dir = var_dir
        self.profiles = profiles
        self.inventory_store = inventory_store
        self.store = store
        self.executor_fn = executor
        self.state_dir = var_dir / "dashboard/applies"
        self.executor = background_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="dashboard-apply"
        )
        self.lock = Lock()

    def _path(self, group_key: str) -> Path:
        return self.state_dir / f"{group_key}.json"

    def _existing_solution_policy(self, profile: Any) -> str:
        get_group = getattr(self.store, "get_group", None)
        group = get_group(str(profile.group_key)) if callable(get_group) else None
        policy = group.get("existing_solution_policy") if group else None
        return (
            str(policy)
            if policy in {"preserve", "rewrite"}
            else str(getattr(profile, "existing_solution_policy", "preserve"))
        )

    def _write(self, state: Mapping[str, Any]) -> dict[str, Any]:
        return write_apply_state(self.state_dir, state)

    def get(self, group_key: str) -> dict[str, Any] | None:
        return read_apply_state(self._path(group_key))

    def _verified_row(self, group_key: str, problem_id: str) -> dict[str, object]:
        return verified_row(self.profiles, self.inventory_store, group_key, problem_id)

    def _verified_group(self, group_key: str) -> list[dict[str, object]]:
        return verified_group(
            self.profiles, self.inventory_store, self.store, group_key
        )

    def start(
        self, group_key: str, problem_id: str, *, force: bool = False
    ) -> dict[str, Any]:
        self._verified_row(group_key, problem_id)
        with self.lock:
            current = self.get(group_key)
            if current and current.get("status") in {"queued", "running", "retry_wait"}:
                raise RuntimeError("apply already active")
            state = self._write(
                {
                    "group_key": group_key,
                    "problem_id": problem_id,
                    "scope": "problem",
                    "force": force,
                    "status": "queued",
                    "queued_at": _now(),
                }
            )
            if force:
                self.executor.submit(self.run_now, group_key, problem_id, force=True)
            else:
                self.executor.submit(self.run_now, group_key, problem_id)
            return state

    def start_group(self, group_key: str) -> dict[str, Any]:
        self._verified_group(group_key)
        with self.lock:
            current = self.get(group_key)
            if current and current.get("status") in {"queued", "running", "retry_wait"}:
                raise RuntimeError("apply already active")
            state = self._write(
                {
                    "group_key": group_key,
                    "scope": "group",
                    "status": "queued",
                    "queued_at": _now(),
                }
            )
            self.executor.submit(self.run_group_now, group_key)
            return state

    def start_helpers(
        self, group_key: str, problem_id: str | None = None
    ) -> dict[str, Any]:
        problem_ids = helper_targets(self.inventory_store, group_key, problem_id)
        with self.lock:
            current = self.get(group_key)
            if current and current.get("status") in {"queued", "running", "retry_wait"}:
                raise RuntimeError("apply already active")
            state = self._write(
                {
                    "group_key": group_key,
                    "problem_id": problem_id,
                    "scope": "problem" if problem_id else "group",
                    "stage": "helpers",
                    "status": "queued",
                    "queued_at": _now(),
                }
            )
            self.executor.submit(
                self.run_helpers_now, group_key, problem_ids, state["scope"]
            )
            return state

    def run_helpers_now(
        self,
        group_key: str,
        problem_ids: tuple[str, ...],
        scope: str | None = None,
    ) -> dict[str, Any]:
        snapshot = self.inventory_store.get(group_key)
        if snapshot is None or snapshot.status != "ready":
            raise ValueError("group has no ready local inventory")
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
            "--group",
            group_key,
            "--confirm-catalog",
            str(snapshot.catalog_snapshot_id),
            "--inventory-db",
            str(self.inventory_store.path),
            "--max-workers",
            "1" if len(problem_ids) == 1 else "5",
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
            completed, last_error = _record_helpers(
                self.inventory_store, group_key, problem_ids, helpers
            )
            items = self.inventory_store.list_items(group_key)
            if self.store is not None:
                self.store.reconcile_problem_counts(group_key, items)
            if completed:
                state.update(status="completed", completed_at=_now())
                if self.store is not None and all(
                    item.get("apply_status") in SUCCESS
                    and item.get("helpers_status") in SUCCESS
                    for item in items
                ):
                    self.store.update_group(group_key, {"column": "done"})
            else:
                state.update(status="failed", completed_at=_now(), error=last_error)
                if self.store is not None:
                    self.store.update_group(group_key, {"column": "issues"})
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

    def run_now(
        self, group_key: str, problem_id: str, *, force: bool = False
    ) -> dict[str, Any]:
        self._verified_row(group_key, problem_id)
        profile = self.profiles[group_key]
        state: dict[str, Any] = {
            "group_key": group_key,
            "problem_id": problem_id,
            "scope": "problem",
            "force": force,
            "status": "running",
            "started_at": _now(),
        }
        self._write(state)
        argv = [
            "--group",
            str(profile.group_key),
            "--confirm-catalog",
            str(profile.catalog_snapshot_id),
            "--inventory-db",
            str(self.inventory_store.path),
            "--max-workers",
            "1",
            "--apply",
            "--existing-solution-policy",
            "rewrite" if force else self._existing_solution_policy(profile),
            "--only-problem-id",
            problem_id,
        ]
        if force:
            argv.append("--force-apply")
        try:
            return_code = self.executor_fn(argv)
            if return_code:
                raise RuntimeError(f"launcher exited with status {return_code}")
            run_dir = _latest_run(self.var_dir, group_key)
            if run_dir is None:
                raise RuntimeError("launcher produced no run report")
            solution_status, helpers_status, error = _record_problem_result(
                self.inventory_store, group_key, problem_id, run_dir
            )
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
                state.update(
                    status="failed",
                    completed_at=_now(),
                    error=str(error or "MCP write or readback failed"),
                )
                if self.store is not None:
                    self.store.update_group(group_key, {"column": "issues"})
            else:
                state.update(
                    status="skipped",
                    completed_at=_now(),
                    message=str(error or "Задача пропущена."),
                )
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
            self.store.update_group(
                group_key, {"agent_status": None, "agent_summary": None}
            )
        argv = [
            "--group",
            str(profile.group_key),
            "--confirm-catalog",
            str(profile.catalog_snapshot_id),
            "--inventory-db",
            str(self.inventory_store.path),
            "--max-workers",
            "5",
            "--apply",
            "--existing-solution-policy",
            self._existing_solution_policy(profile),
        ]
        last_error = "Не все задачи удалось записать и проверить."
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
            completed, last_error = _record_group_results(
                self.inventory_store, group_key, rows, solutions, helpers
            )
        except Exception as exc:  # noqa: BLE001 - persist the result of this single explicit run.
            completed = False
            last_error = " ".join(str(exc).split())[:300]
        items = self.inventory_store.list_items(group_key)
        if self.store is not None:
            self.store.reconcile_problem_counts(group_key, items)
        if completed:
            state.update(status="completed", attempt=1, completed_at=_now())
            state.pop("retry_in_seconds", None)
            state.pop("error", None)
            if self.store is not None:
                self.store.update_group(
                    group_key,
                    {
                        "column": "done",
                        "agent_status": None,
                        "agent_summary": None,
                    },
                )
            return self._write(state)
        if self.store is not None:
            self.store.update_group(group_key, {"column": "issues"})
        state.update(status="failed", attempt=1, completed_at=_now(), error=last_error)
        return self._write(state)
