"""Run registered groups locally for dashboard review without MCP writes."""

from __future__ import annotations

import json
import secrets
import sys
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import Executor, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any

from solution_runner.group_inventory_store import (
    GroupInventoryStore,
    GroupItemStageResult,
)
from solution_runner.pipelines.core.local_inventory import load_group_inventory

from .dry_run_targets import NoDryRunTarget as _exported_NoDryRunTarget
from .dry_run_targets import (
    _child_rows,
    _problem_id,
    _select_problem,
    _source_problem_id,
)
from .previews import fetch_preview, latest_dry_run_manifest, load_preview, save_preview
from .process_logs import run_logged

NoDryRunTarget = _exported_NoDryRunTarget


MODES = {"parent", "random", "all", "problem"}


def _store_dry_run_results(
    store: GroupInventoryStore,
    group_key: str,
    manifest: Mapping[str, Any],
) -> None:
    """Project content-free dry-run outcomes onto initialized task rows."""

    for record in manifest.get("records", []):
        if not isinstance(record, Mapping) or not record.get("problem_id"):
            continue
        raw_status = str(record.get("status") or "")
        status = (
            "ready"
            if raw_status in {"prepared", "planned", "already_complete"}
            else "skipped"
            if raw_status in {"blocked", "skipped"}
            else "failed"
        )
        message = record.get("message") or record.get("error")
        store.update_item_stage(
            GroupItemStageResult(
                group_key=group_key,
                problem_id=str(record["problem_id"]),
                dry_run_status=status,
                error=" ".join(str(message).split())[:500] if message else None,
            )
        )


def _full_dry_run_ready(manifest: Mapping[str, Any]) -> bool:
    records = [
        item for item in manifest.get("records", []) if isinstance(item, Mapping)
    ]
    return bool(records) and all(
        str(item.get("status") or "") in {"prepared", "planned", "already_complete"}
        for item in records
    )


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _launcher_command(
    profile: Any,
    mode: str,
    problem_id: str | None,
    inventory_db: Path | None = None,
    existing_solution_policy: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "solution_runner.launcher",
        "--group",
        str(profile.group_key),
        "--confirm-catalog",
        str(profile.catalog_snapshot_id),
        "--max-workers",
        "5",
    ]
    if inventory_db is not None:
        command.extend(("--inventory-db", str(inventory_db)))
    if existing_solution_policy:
        command.extend(("--existing-solution-policy", existing_solution_policy))
    if mode != "all":
        if not problem_id:
            raise ValueError("selected problem is required")
        command.extend(("--only-problem-id", problem_id))
    return command


def _run_launcher(command: list[str]) -> int:
    return run_logged(command)


class DryRunManager:
    """Serialize local dry-runs and persist their small control state as JSON."""

    def __init__(
        self,
        *,
        var_dir: Path,
        profiles: Mapping[str, Any],
        gateway_factory: Callable[[], Any],
        store: Any | None = None,
        inventory_store: GroupInventoryStore | None = None,
        initializer: Any | None = None,
        launcher: Callable[[list[str]], int] = _run_launcher,
        choose: Callable[
            [Sequence[Mapping[str, Any]]], Mapping[str, Any]
        ] = secrets.choice,
        on_complete: Callable[[str, Mapping[str, Any]], None] | None = None,
        background_executor: Executor | None = None,
    ) -> None:
        self.var_dir = var_dir
        self.profiles = profiles
        self.gateway_factory = gateway_factory
        self.store = store
        self.inventory_store = inventory_store
        self.initializer = initializer
        self.launcher = launcher
        self.choose = choose
        self.on_complete = on_complete
        self.state_dir = var_dir / "dashboard/dry-runs"
        self.preview_dir = var_dir / "dashboard/previews"
        self.executor = background_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="dashboard-dry-run"
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

    def start(self, group_key: str, mode: str) -> dict[str, Any]:
        return self._start(
            group_key, mode, append=False, excluded_problem_ids=frozenset()
        )

    def start_problem(self, group_key: str, problem_id: str) -> dict[str, Any]:
        if not problem_id:
            raise ValueError("problem id is required")
        return self._start(
            group_key,
            "problem",
            append=True,
            excluded_problem_ids=frozenset(),
            requested_problem_id=problem_id,
        )

    def start_additional(self, group_key: str) -> dict[str, Any]:
        preview = load_preview(self.preview_dir, group_key)
        if not preview:
            raise ValueError("group has no preview to extend")
        excluded = frozenset(
            str(sample.get("problem_id"))
            for sample in preview.get("samples", [])
            if isinstance(sample, dict) and sample.get("problem_id")
        )
        return self._start(
            group_key,
            "random",
            append=True,
            excluded_problem_ids=excluded,
        )

    def _start(
        self,
        group_key: str,
        mode: str,
        *,
        append: bool,
        excluded_problem_ids: frozenset[str],
        requested_problem_id: str | None = None,
    ) -> dict[str, Any]:
        if mode not in MODES:
            raise ValueError("unknown dry-run mode")
        if group_key not in self.profiles:
            raise KeyError(group_key)
        with self.lock:
            current = self.get(group_key)
            if current and current.get("status") in {"queued", "running"}:
                raise RuntimeError("dry-run already active")
            state = self._write(
                {
                    "group_key": group_key,
                    "mode": mode,
                    "status": "queued",
                    "selected_problem_id": None,
                    "selected_source_problem_id": None,
                    "append": append,
                    "queued_at": _now(),
                }
            )
            future = self.executor.submit(
                self.run_now,
                group_key,
                mode,
                append=append,
                excluded_problem_ids=excluded_problem_ids,
                requested_problem_id=requested_problem_id,
            )
            if self.on_complete:
                future.add_done_callback(
                    lambda completed: self.on_complete(group_key, completed.result())
                )
            return state

    def run_now(
        self,
        group_key: str,
        mode: str,
        *,
        append: bool = False,
        excluded_problem_ids: frozenset[str] = frozenset(),
        requested_problem_id: str | None = None,
    ) -> dict[str, Any]:
        profile = self.profiles[group_key]
        state = {
            "group_key": group_key,
            "mode": mode,
            "status": "running",
            "selected_problem_id": None,
            "selected_source_problem_id": None,
            "append": append,
            "started_at": _now(),
        }
        gateway = None
        try:
            if self.inventory_store is not None and self.initializer is not None:
                self.initializer.ensure_ready(group_key)
            if mode == "all":
                selected = None
            elif self.inventory_store is not None:
                inventory = load_group_inventory(
                    self.inventory_store,
                    profile,
                    apply_solution_scope=mode not in {"parent", "problem"},
                )
                children = [
                    {
                        "problem_id": target.problem_id,
                        "source_problem_id": target.source_problem_id,
                    }
                    for target in inventory.targets
                ]
                selected = _select_problem(
                    children,
                    mode,
                    choose=self.choose,
                    excluded_problem_ids=excluded_problem_ids,
                    requested_problem_id=requested_problem_id,
                )
            else:
                gateway = self.gateway_factory()
                children = gateway.get_source_catalog_children(
                    profile.source_group_id, "group"
                )
                if (
                    mode == "random"
                    and getattr(profile, "solution_scope", "all") == "missing_only"
                ):
                    missing = gateway.get_source_catalog_missing_solution_summary(
                        profile.source_group_id, "group"
                    )
                    eligible = {
                        str(value) for value in missing.get("source_problem_ids", [])
                    }
                    rows = _child_rows(children)
                    children = rows[:1] + [
                        item
                        for item in rows[1:]
                        if _source_problem_id(item) in eligible
                    ]
                selected = _select_problem(
                    children,
                    mode,
                    choose=self.choose,
                    excluded_problem_ids=excluded_problem_ids,
                    requested_problem_id=requested_problem_id,
                )
            if selected is not None:
                state["selected_problem_id"] = _problem_id(selected)
                state["selected_source_problem_id"] = _source_problem_id(selected)
            self._write(state)
        except NoDryRunTarget:
            state.update(
                status="skipped",
                completed_at=_now(),
                message="В группе нет задач, которые этот раннер должен изменять.",
            )
            return self._write(state)
        except Exception as exc:  # noqa: BLE001 - one group run must terminate locally.
            return self._fail(state, exc)
        finally:
            close = getattr(gateway, "close", None)
            if callable(close):
                close()

        try:
            return_code = self.launcher(
                _launcher_command(
                    profile,
                    mode,
                    state["selected_problem_id"],
                    self.inventory_store.path if self.inventory_store else None,
                    self._existing_solution_policy(profile),
                )
            )
            if return_code:
                raise RuntimeError(f"launcher exited with status {return_code}")
            gateway = self.gateway_factory()
            try:
                manifest = latest_dry_run_manifest(self.var_dir, group_key)
                if manifest is None:
                    raise RuntimeError("launcher produced no current dry-run manifest")
                if self.inventory_store is not None:
                    _store_dry_run_results(self.inventory_store, group_key, manifest)
                fresh_preview = fetch_preview(gateway, profile, manifest)
                if append:
                    preview = load_preview(self.preview_dir, group_key) or {
                        "group_key": group_key,
                        "samples": [],
                    }
                    fresh_by_id = {
                        str(sample.get("problem_id")): sample
                        for sample in fresh_preview.get("samples", [])
                        if isinstance(sample, dict) and sample.get("problem_id")
                    }
                    samples = preview.setdefault("samples", [])
                    preview["samples"] = [
                        fresh_by_id.pop(str(sample.get("problem_id")), sample)
                        for sample in samples
                    ] + list(fresh_by_id.values())
                    preview["fetched_at"] = fresh_preview["fetched_at"]
                else:
                    preview = fresh_preview
                save_preview(self.preview_dir, preview)
            finally:
                close = getattr(gateway, "close", None)
                if callable(close):
                    close()
            full_ready = mode != "all" or _full_dry_run_ready(manifest)
            state.update(
                status="completed" if full_ready else "completed_with_errors",
                completed_at=_now(),
            )
            if self.store is not None and mode == "all":
                self.store.update_group(
                    group_key,
                    {
                        "column": "review" if full_ready else "issues",
                        "full_dry_run_status": "ready" if full_ready else "failed",
                    },
                )
            return self._write(state)
        except Exception as exc:  # noqa: BLE001 - persist isolated terminal failure.
            return self._fail(state, exc)

    def _fail(self, state: Mapping[str, Any], exc: Exception) -> dict[str, Any]:
        failed = dict(state)
        failed.update(
            status="failed",
            completed_at=_now(),
            error=" ".join(str(exc).split())[:300],
        )
        if self.store is not None and state.get("mode") == "all":
            self.store.update_group(
                str(state["group_key"]),
                {
                    "column": "issues",
                    "full_dry_run_status": "failed",
                },
            )
        return self._write(failed)
