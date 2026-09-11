"""Small localhost-only HTTP API for the group dashboard."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from solution_runner.pipelines.core.group_profiles import all_group_profiles
from solution_runner.pipelines.grid_polygon.mcp_runtime import DEFAULT_MCP_URL, JsonRpcMcpGateway
from solution_runner.group_inventory_store import GroupInventoryStore

from .initialization import GroupInitializer
from .previews import ProblemPreviewUnavailable, fetch_problem_preview, load_preview
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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
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
        navigation = teacherhelper_navigation(profile) if profile else None
        if navigation:
            group["teacherhelper"] = navigation
        return group

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._json(204, {})

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
            self._json(200, {"groups": groups, "summary": _summary(groups)})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "comments":
            self._json(200, {"comments": self.server.store.list_comments(segments[2])})
            return
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "preview":
            preview = load_preview(self.server.preview_dir, segments[2])
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
        if len(segments) == 4 and segments[:2] == ["api", "groups"] and segments[3] == "register":
            if self.server.codex_tasks is None or self.server.inventory_store is None:
                self._json(503, {"error": "codex_registration_unavailable"})
                return
            group = self.server.store.get_group(segments[2])
            snapshot = self.server.inventory_store.get(segments[2])
            if group is None or snapshot is None:
                self._json(404, {"error": "group_inventory_not_found"})
                return
            if group["column"] != "queue":
                self._json(409, {"error": "group_not_waiting_for_registration"})
                return
            thread_id = str(self._body().get("thread_id") or "").strip() or None
            inventory = {
                "parent_problem_id": snapshot.parent_problem_id,
                "parent_source_problem_id": snapshot.parent_source_problem_id,
                "task_count": len(self.server.inventory_store.list_items(segments[2])),
            }
            try:
                task = self.server.codex_tasks.register_group(group, inventory, thread_id)
            except ValueError as exc:
                self._json(409, {"error": "invalid_codex_task", "message": str(exc)})
                return
            except RuntimeError as exc:
                self._json(502, {"error": "codex_registration_failed", "message": str(exc)})
                return
            updated = self.server.store.update_group(segments[2], {
                "codex_thread_id": task["id"],
                "task_title": task["title"],
                "task_url": f"codex://threads/{task['id']}",
                "column": "work",
                "revision_requested": 0,
                "full_dry_run_status": None,
            })
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
            group_key = str(body.get("id", "")).strip()
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
            body = str(self._body().get("body", "")).strip()
            if not body:
                self._json(400, {"error": "comment_required"})
                return
            if group["column"] in {"issues", "review"}:
                thread_id = group.get("codex_thread_id")
                if not thread_id or self.server.codex_tasks is None:
                    self._json(409, {"error": "codex_task_not_linked"})
                    return
                try:
                    self.server.codex_tasks.send_comment(str(thread_id), group, body)
                except RuntimeError as exc:
                    self._json(502, {"error": "codex_comment_failed", "message": str(exc)})
                    return
            comment = self.server.store.add_comment(segments[2], body)
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
    dry_runs = DryRunManager(
        var_dir=args.var,
        profiles=profiles,
        gateway_factory=gateway_factory,
        store=store,
        inventory_store=inventory_store,
    ) if api_key else None
    applies = ApplyManager(
        var_dir=args.var,
        profiles=profiles,
        inventory_store=inventory_store,
        store=store,
    ) if api_key else None
    initializer = GroupInitializer(
        profiles=profiles,
        inventory_store=inventory_store,
        gateway_factory=gateway_factory,
        group_source_lookup=store.get_group,
        on_complete=lambda group_key, state: store.update_group(
            group_key, {"column": "queue"}
        ) if state.get("status") == "ready" else None,
    ) if api_key else None
    codex_tasks = CodexTaskService(project_root=project_root)
    server = make_server(store=store, var_dir=args.var, profiles=profiles, static_dir=args.static, preview_dir=args.previews, dry_runs=dry_runs, applies=applies, initializer=initializer, inventory_store=inventory_store, preview_gateway_factory=gateway_factory if api_key else None, codex_tasks=codex_tasks, host=args.host, port=args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
