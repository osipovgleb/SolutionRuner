"""Small localhost-only HTTP API for the group dashboard."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from threading import Event, Thread
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.grid_polygon.mcp_runtime import DEFAULT_MCP_URL, JsonRpcMcpGateway
from solution_runner.group_inventory_store import GroupInventoryStore

from .initialization import GroupInitializer
from .catalogs import load_catalogs
from .store import normalize_group_key
from .previews import (
    ProblemPreviewUnavailable,
    append_preview_sample,
    fetch_preview,
    fetch_problem_preview,
    latest_dry_run_manifest,
    load_preview,
    save_preview,
)
from .rejections import reject_indexed_problem
from .dry_runs import DryRunManager
from .applies import ApplyManager
from .activity import load_group_activity
from .backfill import backfill_local_runs
from .store import DashboardStore, sync_groups
from .teacherhelper import teacherhelper_navigation
from .codex_tasks import CodexTaskService


class DashboardServer(ThreadingHTTPServer):
    store: DashboardStore
    var_dir: Path
    profiles: Mapping[str, Any]
    static_dir: Path
    preview_dir: Path
    dry_runs: Any | None
    applies: Any | None
    initializer: Any | None
    inventory_store: GroupInventoryStore | None
    preview_gateway_factory: Any | None
    codex_tasks: Any | None
    jobs_started_at: datetime


ACTIVE_JOB_STATUSES = {"queued", "running", "retry_wait"}


def _job_timestamp(state: Mapping[str, Any]) -> datetime | None:
    raw = state.get("queued_at") or state.get("started_at")
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _register_group_task(
    store: DashboardStore,
    inventory_store: GroupInventoryStore,
    codex_tasks: CodexTaskService,
    group_key: str,
    thread_id: str | None = None,
    comment: str = "",
) -> tuple[dict[str, str], dict[str, Any]]:
    group = store.get_group(group_key)
    snapshot = inventory_store.get(group_key)
    if group is None or snapshot is None:
        raise KeyError(group_key)
    inventory = {
        "parent_problem_id": snapshot.parent_problem_id,
        "parent_source_problem_id": snapshot.parent_source_problem_id,
        "task_count": len(inventory_store.list_items(group_key)),
    }
    task = (
        codex_tasks.register_group(group, inventory, thread_id, comment)
        if comment else codex_tasks.register_group(group, inventory, thread_id)
    )
    updated = store.update_group(group_key, {
        "codex_thread_id": task["id"],
        "codex_archived": 0,
        "task_title": task["title"],
        "task_url": f"codex://threads/{task['id']}",
        "column": "work",
        "revision_requested": 0,
        "full_dry_run_status": None,
        "agent_status": "working",
        "agent_summary": "Агент исследует группу и готовит полный dry-run.",
    })
    assert updated is not None
    return task, updated


def _handle_codex_exit(
    store: DashboardStore,
    thread_id: str,
    return_code: int,
    dry_runs: Any | None = None,
) -> bool:
    group = next((item for item in store.list_groups() if item.get("codex_thread_id") == thread_id), None)
    if not group:
        return False
    if group.get("agent_status") in {"updated", "no_changes"}:
        if group.get("full_dry_run_status") == "ready":
            return group.get("agent_status") == "updated"
        if dry_runs is None:
            store.update_group(str(group["id"]), {
                "agent_status": "blocked",
                "agent_summary": "Результат агента не подтверждён полным dry-run.",
            })
            return False
        store.update_group(str(group["id"]), {
            "agent_status": "verifying",
            "full_dry_run_status": "running",
            "agent_summary": "Сервер проверяет результат полным dry-run.",
        })
        try:
            dry_runs.start(str(group["id"]), "all")
        except (KeyError, ValueError, RuntimeError) as exc:
            store.update_group(str(group["id"]), {
                "agent_status": "blocked",
                "full_dry_run_status": "failed",
                "agent_summary": f"Полный dry-run не запущен: {' '.join(str(exc).split())}"[:200],
            })
        return False
    if group.get("agent_status") != "working":
        return False
    store.update_group(str(group["id"]), {
        "agent_status": "blocked" if return_code else "needs_input",
        "agent_summary": (
            f"Codex завершился с кодом {return_code}; открой задачу и повтори запуск."
            if return_code else
            "Codex остановился без итогового статуса; открой задачу — возможно, нужен ответ."
        ),
    })
    return False


def _finish_initialization(
    store: DashboardStore,
    inventory_store: GroupInventoryStore,
    codex_tasks: CodexTaskService,
    group_key: str,
    state: Mapping[str, Any],
) -> None:
    if state.get("status") != "ready":
        store.update_group(group_key, {
            "agent_status": "blocked",
            "agent_summary": f"Инициализация не завершена: {state.get('error') or 'неизвестная ошибка'}"[:200],
        })
        return
    store.update_group(group_key, {
        "column": "queue",
        "agent_status": None,
        "agent_summary": "Инициализация завершена. Группа готова к ручной регистрации из проекта.",
    })


def _finish_automatic_dry_run(
    store: DashboardStore,
    group_key: str,
    state: Mapping[str, Any],
) -> None:
    group = store.get_group(group_key)
    if not group or group.get("agent_status") != "verifying" or state.get("mode") != "all":
        return
    completed = state.get("status") == "completed"
    store.update_group(group_key, {
        "agent_status": "updated" if completed else "blocked",
        "agent_summary": (
            "Полный dry-run завершён успешно."
            if completed else
            f"Полный dry-run не прошёл: {state.get('error') or state.get('status')}"
        )[:200],
    })


def _resume_automatic_groups(
    store: DashboardStore,
    inventory_store: GroupInventoryStore,
    codex_tasks: CodexTaskService,
) -> None:
    for group in store.list_groups():
        group_key = str(group["id"])
        if group.get("agent_status"):
            store.update_group(group_key, {"agent_status": group["agent_status"]})
        snapshot = inventory_store.get(group_key)
        if (
            group.get("column") == "initialization"
            and snapshot is not None
            and snapshot.status == "ready"
            and not group.get("codex_thread_id")
        ):
            _finish_initialization(
                store, inventory_store, codex_tasks, group_key, {"status": "ready"}
            )


class Handler(BaseHTTPRequestHandler):
    server: DashboardServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            value = json.loads(self.rfile.read(length) or b"{}")
            return value if isinstance(value, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def _segments(self) -> list[str]:
        return [unquote(part) for part in urlparse(self.path).path.split("/") if part]

    def _group_payload(self, group: dict[str, Any] | None) -> dict[str, Any] | None:
        if group is None:
            return None
        profile = self.server.profiles.get(str(group["id"]))
        navigation = teacherhelper_navigation(profile) if profile else group.get("teacherhelper")
        if navigation:
            group["teacherhelper"] = navigation
        candidates: list[dict[str, Any]] = []
        for manager, default_kind in (
            (self.server.dry_runs, "dry_run"),
            (self.server.applies, "apply"),
        ):
            state = manager.get(str(group["id"])) if manager else None
            if not state or state.get("status") not in ACTIVE_JOB_STATUSES:
                continue
            timestamp = _job_timestamp(state)
            if timestamp and timestamp < self.server.jobs_started_at:
                continue
            candidates.append({
                "kind": "helpers" if state.get("stage") == "helpers" else default_kind,
                "status": state["status"],
                "scope": state.get("scope") or ("problem" if state.get("mode") == "problem" else "group"),
            })
        if candidates:
            priority = {"running": 2, "retry_wait": 1, "queued": 0}
            group["job"] = max(candidates, key=lambda item: priority[item["status"]])
            group["column"] = "jobs"
        return group

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._json(204, {})

    def do_DELETE(self) -> None:  # noqa: N802
        segments = self._segments()
        if len(segments) != 3 or segments[:2] != ["api", "groups"]:
            self._json(404, {"error": "not_found"})
            return
        group_key = segments[2]
        group = self._group_payload(self.server.store.get_group(group_key))
        if group is None:
            self._json(404, {"error": "group_not_found"})
            return
        initialization = self.server.initializer.get(group_key) if self.server.initializer else {}
        if (group.get("job") or group.get("agent_status") in {"working", "verifying"}
                or initialization.get("status") in {"pending", "running"}):
            self._json(409, {"error": "group_is_running"})
            return
        self.server.store.remove_group(group_key)
        self._json(200, {"removed": True})

    def do_GET(self) -> None:  # noqa: N802
        segments = self._segments()
        if segments == ["api", "codex", "tasks"]:
            if self.server.codex_tasks is None:
                self._json(503, {"error": "codex_tasks_unavailable"})
                return
            try:
                tasks = self.server.codex_tasks.list_tasks()
            except RuntimeError as exc:
                self._json(502, {"error": "codex_tasks_unavailable", "message": str(exc)})
            else:
                self._json(200, {"tasks": tasks})
            return
        if segments == ["api", "groups"]:
            groups = self.server.store.list_groups()
            for group in groups:
                self._group_payload(group)
            self._json(200, {
                "groups": groups, "summary": _summary(groups),
                "catalogs": [{"id": key, "name": name} for key, name in load_catalogs().items()],
            })
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "comments":
            self._json(200, {"comments": self.server.store.list_comments(segments[2])})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "preview":
            preview = load_preview(self.server.preview_dir, segments[2])
            profile = self.server.profiles.get(segments[2])
            if preview is None and profile is not None and self.server.preview_gateway_factory is not None:
                gateway = self.server.preview_gateway_factory()
                try:
                    manifest = latest_dry_run_manifest(self.server.var_dir, segments[2])
                    if manifest is not None:
                        preview = fetch_preview(gateway, profile, manifest)
                        save_preview(self.server.preview_dir, preview)
                finally:
                    close = getattr(gateway, "close", None)
                    if callable(close):
                        close()
            self._json(200, preview) if preview else self._json(404, {"error": "preview_not_found"})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "dry-run":
            state = self.server.dry_runs.get(segments[2]) if self.server.dry_runs else None
            self._json(200, state) if state else self._json(404, {"error": "dry_run_not_found"})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "apply":
            state = self.server.applies.get(segments[2]) if self.server.applies else None
            self._json(200, state) if state else self._json(404, {"error": "apply_not_found"})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "initialization":
            state = self.server.initializer.get(segments[2]) if self.server.initializer else None
            self._json(200, state) if state else self._json(503, {"error": "initializer_unavailable"})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "tasks":
            inventory = self.server.inventory_store
            snapshot = inventory.get(segments[2]) if inventory else None
            if snapshot is None:
                self._json(404, {"error": "inventory_not_found"})
                return
            assets_by_problem: dict[str, list[dict[str, str]]] = {}
            for asset in snapshot.assets:
                assets_by_problem.setdefault(asset.problem_id, []).append({
                    "asset_id": asset.asset_id,
                    "asset_key": asset.asset_key,
                    "section": asset.section_key,
                    "content_type": asset.content_type,
                })
            tasks = inventory.list_items(segments[2])
            for task in tasks:
                task["assets"] = assets_by_problem.get(str(task["problem_id"]), [])
            self._json(200, {
                "status": snapshot.status,
                "error": snapshot.error,
                "parent_problem_id": snapshot.parent_problem_id,
                "tasks": tasks,
            })
            return
        if len(segments) == 6 and segments[:2] == ["api", "groups"] and segments[3] == "tasks" and segments[5] == "preview":
            inventory = self.server.inventory_store
            task = next((
                item for item in (inventory.list_items(segments[2]) if inventory else [])
                if str(item.get("problem_id")) == segments[4]
            ), None)
            if task is None:
                self._json(404, {"error": "problem_not_found"})
                return
            if self.server.preview_gateway_factory is None:
                self._json(503, {"error": "preview_unavailable"})
                return
            gateway = self.server.preview_gateway_factory()
            preview = None
            try:
                profile = self.server.profiles.get(segments[2])
                if profile is not None:
                    try:
                        cached = append_preview_sample(
                            gateway,
                            profile,
                            self.server.preview_dir,
                            self.server.var_dir,
                            source_problem_id=str(task["source_problem_id"]),
                        )
                        preview = {
                            **cached,
                            "samples": [
                                sample for sample in cached.get("samples", [])
                                if str(sample.get("problem_id")) == segments[4]
                            ],
                        }
                    except ValueError:
                        pass
                if not preview or not preview.get("samples"):
                    preview = fetch_problem_preview(
                        gateway,
                        self.server.preview_dir,
                        segments[2],
                        segments[4],
                        str(task["source_problem_id"]),
                    )
            except ProblemPreviewUnavailable:
                self._json(404, {"error": "problem_not_available"})
            finally:
                close = getattr(gateway, "close", None)
                if callable(close):
                    close()
            if preview is not None:
                self._json(200, preview)
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "activity":
            if self.server.store.get_group(segments[2]) is None:
                self._json(404, {"error": "group_not_found"})
                return
            self._json(200, load_group_activity(
                self.server.var_dir, segments[2], self.server.inventory_store
            ))
            return
        if len(segments) == 3 and segments[:2] == ["api", "groups"]:
            group = self._group_payload(self.server.store.get_group(segments[2]))
            self._json(200, group) if group else self._json(404, {"error": "group_not_found"})
            return
        self._static()

    def do_PATCH(self) -> None:  # noqa: N802
        segments = self._segments()
        if len(segments) != 3 or segments[:2] != ["api", "groups"]:
            self._json(404, {"error": "not_found"})
            return
        body = self._body()
        if body.get("column") not in {None, "initialization", "queue", "work", "review", "issues", "done"}:
            self._json(400, {"error": "invalid_column"})
            return
        editable = {
            "column", "title", "task_title", "task_url", "revision_requested",
            "existing_solution_policy", "condition_image_policy", "solution_image_policy",
            "verify_answers", "verify_helpers", "agent_sample_size",
        }
        changes = {key: value for key, value in body.items() if key in editable}
        group = self._group_payload(self.server.store.update_group(segments[2], changes))
        self._json(200, group) if group else self._json(404, {"error": "group_not_found"})

    def do_POST(self) -> None:  # noqa: N802
        segments = self._segments()
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "archive-codex":
            group = self.server.store.get_group(segments[2])
            if group is None:
                self._json(404, {"error": "group_not_found"})
                return
            if group["column"] != "done":
                self._json(409, {"error": "group_not_done"})
                return
            thread_id = group.get("codex_thread_id")
            if not thread_id or self.server.codex_tasks is None:
                self._json(409, {"error": "codex_task_not_linked"})
                return
            if group.get("codex_archived"):
                self._json(200, {"group": self._group_payload(group)})
                return
            try:
                self.server.codex_tasks.archive_task(str(thread_id))
            except RuntimeError as exc:
                self._json(502, {"error": "codex_archive_failed", "message": str(exc)})
                return
            updated = self.server.store.update_group(segments[2], {"codex_archived": 1})
            self._json(200, {"group": self._group_payload(updated)})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "register":
            if self.server.codex_tasks is None or self.server.inventory_store is None:
                self._json(503, {"error": "codex_registration_unavailable"})
                return
            body = self._body()
            thread_id = str(body.get("thread_id") or "").strip() or None
            comment = str(body.get("comment") or "").strip()
            try:
                task, updated = _register_group_task(
                    self.server.store,
                    self.server.inventory_store,
                    self.server.codex_tasks,
                    segments[2],
                    thread_id,
                    comment,
                )
            except KeyError:
                self._json(404, {"error": "group_inventory_not_found"})
                return
            except ValueError as exc:
                self._json(409, {"error": "invalid_codex_task", "message": str(exc)})
                return
            except RuntimeError as exc:
                self._json(502, {"error": "codex_registration_failed", "message": str(exc)})
                return
            self._json(202, {"task": task, "group": self._group_payload(updated)})
            return
        if len(segments) == 6 and segments[:2] == ["api", "groups"] and segments[3] == "tasks" and segments[5] == "reject":
            if self.server.preview_gateway_factory is None or self.server.inventory_store is None:
                self._json(503, {"error": "rejection_unavailable"})
                return
            reason = str(self._body().get("reason") or "").strip()
            if not reason:
                self._json(400, {"error": "reason_required"})
                return
            gateway = self.server.preview_gateway_factory()
            try:
                rejection = reject_indexed_problem(
                    gateway,
                    self.server.inventory_store,
                    self.server.preview_dir,
                    segments[2],
                    segments[4],
                    reason,
                )
            except KeyError:
                self._json(404, {"error": "problem_not_found"})
                return
            except ValueError as exc:
                self._json(409, {"error": "problem_not_rejectable", "message": str(exc)})
                return
            except RuntimeError:
                self._json(502, {"error": "rejection_not_confirmed"})
                return
            finally:
                close = getattr(gateway, "close", None)
                if callable(close):
                    close()
            items = self.server.inventory_store.list_items(segments[2])
            self.server.store.reconcile_problem_counts(segments[2], items)
            self._json(200, {
                "rejection": rejection,
                "group": self._group_payload(self.server.store.get_group(segments[2])),
            })
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "initialization":
            if self.server.initializer is None:
                self._json(503, {"error": "initializer_unavailable"})
                return
            try:
                state = self.server.initializer.start(segments[2])
            except (KeyError, ValueError):
                self._json(404, {"error": "group_not_found"})
            except RuntimeError as exc:
                self._json(409, {"error": "initialization_not_started", "message": str(exc)})
            else:
                self._json(202, state)
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "dry-run":
            if self.server.dry_runs is None:
                self._json(503, {"error": "dry_runs_unavailable"})
                return
            body = self._body()
            mode = str(body.get("mode") or "")
            try:
                if mode == "problem":
                    state = self.server.dry_runs.start_problem(
                        segments[2], str(body.get("problem_id") or "")
                    )
                else:
                    state = self.server.dry_runs.start(segments[2], mode)
            except KeyError:
                self._json(404, {"error": "group_profile_not_found"})
            except ValueError:
                self._json(400, {"error": "invalid_dry_run_mode"})
            except RuntimeError:
                self._json(409, {"error": "dry_run_already_active"})
            else:
                self._json(202, state)
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "apply":
            if self.server.applies is None:
                self._json(503, {"error": "applies_unavailable"})
                return
            body = self._body()
            problem_id = str(body.get("problem_id") or "")
            try:
                if body.get("stage") == "helpers":
                    state = self.server.applies.start_helpers(
                        segments[2], None if body.get("scope") == "group" else problem_id
                    )
                else:
                    state = (
                        self.server.applies.start_group(segments[2])
                        if body.get("scope") == "group"
                        else self.server.applies.start(segments[2], problem_id)
                    )
            except KeyError:
                self._json(404, {"error": "group_profile_not_found"})
            except ValueError as exc:
                self._json(409, {"error": "problem_not_ready", "message": str(exc)})
            except RuntimeError:
                self._json(409, {"error": "apply_already_active"})
            else:
                self._json(202, state)
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "preview":
            if self.server.dry_runs is None:
                self._json(503, {"error": "dry_runs_unavailable"})
                return
            try:
                state = self.server.dry_runs.start_additional(segments[2])
            except ValueError:
                self._json(409, {"error": "preview_task_not_found"})
            except RuntimeError:
                self._json(409, {"error": "dry_run_already_active"})
            else:
                self._json(202, state)
            return
        if segments == ["api", "groups"]:
            body = self._body()
            group_key = normalize_group_key(str(body.get("id", "")))
            catalog_id = str(body.get("catalog_id", "")).strip()
            if not group_key or not catalog_id:
                self._json(400, {"error": "group_id_and_catalog_required"})
                return
            try:
                group = self.server.store.add_manual_group(group_key, catalog_id, body)
            except ValueError:
                self._json(409, {"error": "group_already_exists"})
                return
            note = str(body.get("note", "")).strip()
            if note:
                self.server.store.add_comment(group_key, note)
            if self.server.initializer is not None:
                self.server.initializer.start(group_key)
            else:
                group = self.server.store.update_group(group_key, {
                    "agent_status": "blocked",
                    "agent_summary": "Инициализация недоступна: dashboard запущен без TeacherHelper API key.",
                })
            self._json(201, self._group_payload(group))
            return
        if segments == ["api", "sync"]:
            result = sync_groups(
                self.server.store,
                self.server.profiles,
                self.server.var_dir,
                inventory_store=self.server.inventory_store,
            )
            self._json(200, result)
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "comments":
            group = self.server.store.get_group(segments[2])
            if group is None:
                self._json(404, {"error": "group_not_found"})
                return
            payload = self._body()
            body = str(payload.get("body", "")).strip()
            if not body:
                self._json(400, {"error": "comment_required"})
                return
            problem_id = str(payload.get("problem_id") or "").strip() or None
            source_problem_id = None
            if problem_id:
                item = next((
                    item for item in (self.server.inventory_store.list_items(segments[2]) if self.server.inventory_store else [])
                    if str(item.get("problem_id")) == problem_id
                ), None)
                if item is None:
                    self._json(404, {"error": "problem_not_found"})
                    return
                source_problem_id = str(item["source_problem_id"])
            thread_id = group.get("codex_thread_id")
            must_send = (
                group["column"] in {"issues", "review"}
                or group.get("agent_status") in {"blocked", "needs_input"}
                or problem_id
            )
            sent_to_codex = False
            if thread_id:
                if self.server.codex_tasks is None:
                    self._json(503, {"error": "codex_tasks_unavailable"})
                    return
                try:
                    if source_problem_id:
                        self.server.codex_tasks.send_comment(str(thread_id), group, body, source_problem_id)
                    else:
                        self.server.codex_tasks.send_comment(str(thread_id), group, body)
                except RuntimeError as exc:
                    self._json(502, {"error": "codex_comment_failed", "message": str(exc)})
                    return
                sent_to_codex = True
            elif must_send:
                    self._json(409, {"error": "codex_task_not_linked"})
                    return
            comment = self.server.store.add_comment(segments[2], body, problem_id)
            if sent_to_codex:
                self.server.store.update_group(segments[2], {
                    "agent_status": "working",
                    "agent_summary": None,
                })
            self._json(201, {
                "comment": comment,
                "group": self._group_payload(self.server.store.get_group(segments[2])),
            })
            return
        self._json(404, {"error": "not_found"})

    def _static(self) -> None:
        path = urlparse(self.path).path.lstrip("/") or "index.html"
        candidate = (self.server.static_dir / path).resolve()
        root = self.server.static_dir.resolve()
        if root not in candidate.parents and candidate != root:
            self.send_error(404)
            return
        if not candidate.is_file():
            candidate = root / "index.html"
        if not candidate.is_file():
            self.send_error(404, "Dashboard build not found")
            return
        body = candidate.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(candidate.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _summary(groups: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "groups": len(groups),
        "transformed": sum(group["transformed"] for group in groups),
        "helpers": sum(group["helpers"] for group in groups),
        "errors": sum(group["stats"]["errors"] for group in groups),
    }


def make_server(*, store: DashboardStore, var_dir: Path, profiles: Mapping[str, Any], static_dir: Path, preview_dir: Path | None = None, dry_runs: Any | None = None, applies: Any | None = None, initializer: Any | None = None, inventory_store: GroupInventoryStore | None = None, preview_gateway_factory: Any | None = None, codex_tasks: Any | None = None, host: str = "127.0.0.1", port: int = 8765) -> DashboardServer:
    server = DashboardServer((host, port), Handler)
    server.store = store
    server.var_dir = var_dir
    server.profiles = profiles
    server.static_dir = static_dir
    server.preview_dir = preview_dir or var_dir / "dashboard/previews"
    server.dry_runs = dry_runs
    server.applies = applies
    server.initializer = initializer
    server.inventory_store = inventory_store
    server.preview_gateway_factory = preview_gateway_factory
    server.codex_tasks = codex_tasks
    server.jobs_started_at = datetime.now(timezone.utc)
    return server


def main(argv: list[str] | None = None) -> int:
    project_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description="Serve the local SolutionRunner group dashboard")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=project_root / "var/dashboard/dashboard.sqlite3")
    parser.add_argument("--var", type=Path, default=project_root / "var")
    parser.add_argument("--static", type=Path, default=project_root / "dashboard/dist")
    parser.add_argument("--previews", type=Path, default=project_root / "var/dashboard/previews")
    args = parser.parse_args(argv)

    store = DashboardStore(args.db)
    profiles = all_group_profiles()
    inventory_store = GroupInventoryStore(args.db)
    backfill_local_runs(inventory_store, args.var, profiles)
    result = sync_groups(
        store,
        profiles,
        args.var,
        inventory_store=inventory_store,
    )
    print(f"Dashboard: {result['groups']} groups, {result['runs']} with runs, {result['warnings']} warnings")
    print(f"Open on http://{args.host}:{args.port}")
    api_key = os.environ.get("TEACHERHELPER_MCP_API_KEY", "").strip()
    gateway_factory = lambda: JsonRpcMcpGateway(
        url=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
        api_key=api_key,
        timeout_seconds=45,
    )
    runner_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dashboard-run")
    dry_runs = DryRunManager(
        var_dir=args.var,
        profiles=profiles,
        gateway_factory=gateway_factory,
        store=store,
        inventory_store=inventory_store,
        on_complete=None,
        background_executor=runner_executor,
    ) if api_key else None
    applies = ApplyManager(
        var_dir=args.var,
        profiles=profiles,
        inventory_store=inventory_store,
        store=store,
        background_executor=runner_executor,
    ) if api_key else None
    restart_requested = Event()
    server: DashboardServer | None = None

    def restart_dashboard() -> None:
        restart_requested.set()
        if server is not None:
            server.shutdown()

    def on_dry_run_complete(group_key: str, state: Mapping[str, Any]) -> None:
        _finish_automatic_dry_run(store, group_key, state)
        group = store.get_group(group_key) or {}
        if (
            state.get("mode") == "all"
            and state.get("status") == "completed"
            and group.get("agent_status") == "updated"
        ):
            restart_dashboard()

    if dry_runs is not None:
        dry_runs.on_complete = on_dry_run_complete

    codex_tasks = CodexTaskService(
        project_root=project_root,
        on_exit=lambda thread_id, code: (
            restart_dashboard()
            if _handle_codex_exit(store, thread_id, code, dry_runs)
            else None
        ),
    )

    initializer = GroupInitializer(
        profiles=profiles,
        inventory_store=inventory_store,
        gateway_factory=gateway_factory,
        group_source_lookup=store.get_group,
        on_resolved=lambda group_key, navigation: store.update_group(
            group_key, {"teacherhelper": navigation}
        ),
        on_complete=lambda group_key, state: _finish_initialization(
            store, inventory_store, codex_tasks, group_key, state
        ),
    ) if api_key else None
    server = make_server(store=store, var_dir=args.var, profiles=profiles, static_dir=args.static, preview_dir=args.previews, dry_runs=dry_runs, applies=applies, initializer=initializer, inventory_store=inventory_store, preview_gateway_factory=gateway_factory if api_key else None, codex_tasks=codex_tasks, host=args.host, port=args.port)
    Thread(
        target=_resume_automatic_groups,
        args=(store, inventory_store, codex_tasks),
        daemon=True,
    ).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    if restart_requested.is_set():
        os.execv(sys.executable, [sys.executable, "-m", "solution_runner.dashboard.server", *sys.argv[1:]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
