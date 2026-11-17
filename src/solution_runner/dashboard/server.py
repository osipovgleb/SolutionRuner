"""Group dashboard API with optional authenticated remote access."""

from __future__ import annotations

import argparse
import json
import logging
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Event, Thread
from typing import Any
from urllib.parse import unquote, urlparse

from solution_runner.group_inventory_store import GroupInventoryStore
from solution_runner.pipelines.core.group_profiles import (
    all_group_profiles,
    reload_group_profiles,
)
from solution_runner.pipelines.grid_polygon.mcp_runtime import (
    DEFAULT_MCP_URL,
    JsonRpcMcpGateway,
)

from . import server_tasks as _server_tasks
from .applies import ApplyManager
from .auth import DashboardAuth
from .backfill import backfill_local_runs
from .codex_tasks import CodexTaskService
from .dry_runs import DryRunManager
from .initialization import GroupInitializer
from .job_queue import DurableJobQueue
from .server_read_routes import DashboardReadRoutes
from .server_tasks import (
    _finish_automatic_dry_run,
    _finish_initialization,
    _handle_codex_exit,
    _resume_automatic_groups,
)
from .server_update_routes import DashboardUpdateRoutes
from .server_write_routes import DashboardWriteRoutes
from .store import DashboardStore, sync_groups
from .teacherhelper import teacherhelper_navigation


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
    auth: DashboardAuth
    job_queue: DurableJobQueue | None


ACTIVE_JOB_STATUSES = {"queued", "running", "retry_wait"}


def _profile_source_state(project_root: Path) -> dict[Path, int]:
    """Return the profile declarations which require a fresh server process."""

    source_root = project_root / "src/solution_runner/pipelines"
    sources = set(source_root.rglob("*profiles.py")) | set(
        source_root.rglob("*handlers.py")
    )
    return {path: path.stat().st_mtime_ns for path in sources if path.is_file()}


def _refresh_server_profiles(server: DashboardServer) -> None:
    profiles = reload_group_profiles()
    server.profiles = profiles
    for manager in (server.dry_runs, server.applies, server.initializer):
        if manager is not None:
            manager.profiles = profiles
    sync_groups(
        server.store,
        profiles,
        server.var_dir,
        inventory_store=server.inventory_store,
    )


def _watch_profile_sources(
    server: DashboardServer,
    project_root: Path,
    stop: Event,
) -> None:
    known = _profile_source_state(project_root)
    while not stop.wait(1):
        current = _profile_source_state(project_root)
        if current == known:
            continue
        try:
            _refresh_server_profiles(server)
        except Exception:
            logging.getLogger(__name__).exception(
                "Failed to reload dashboard profiles; retrying"
            )
            continue
        known = current


def _job_timestamp(state: Mapping[str, Any]) -> datetime | None:
    raw = state.get("queued_at") or state.get("started_at")
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


_register_group_task = _server_tasks._register_group_task


class Handler(
    DashboardReadRoutes,
    DashboardUpdateRoutes,
    DashboardWriteRoutes,
    BaseHTTPRequestHandler,
):
    server: DashboardServer

    def parse_request(self) -> bool:
        if not super().parse_request():
            return False
        auth = self.server.auth
        if auth.enabled and not auth.authorized(self.headers.get("Authorization", "")):
            self.send_response(401)
            self.send_header(
                "WWW-Authenticate", 'Basic realm="SolutionRunner", charset="UTF-8"'
            )
            self.send_header("Content-Length", "0")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return False
        if self.command in {"POST", "PATCH", "DELETE"}:
            origin = self.headers.get("Origin")
            allowed = auth.origin_allowed(origin, self.headers.get("Host", ""))
            if not auth.enabled and origin == "http://127.0.0.1:5173":
                allowed = True
            if not allowed:
                self._json(403, {"error": "cross_origin_request"})
                return False
        return True

    def log_message(self, format: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if not self.server.auth.enabled:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:5173")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header(
            "Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS"
        )
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
        navigation = (
            teacherhelper_navigation(profile) if profile else group.get("teacherhelper")
        )
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
            if (
                self.server.job_queue is None
                and timestamp
                and timestamp < self.server.jobs_started_at
            ):
                continue
            candidates.append(
                {
                    "kind": "helpers"
                    if state.get("stage") == "helpers"
                    else default_kind,
                    "status": state["status"],
                    "scope": state.get("scope")
                    or ("problem" if state.get("mode") == "problem" else "group"),
                }
            )
        if candidates:
            priority = {"running": 2, "retry_wait": 1, "queued": 0}
            group["job"] = max(candidates, key=lambda item: priority[item["status"]])
            group["column"] = "jobs"
        return group

    def do_OPTIONS(self) -> None:
        self._json(204, {})


def make_server(
    *,
    store: DashboardStore,
    var_dir: Path,
    profiles: Mapping[str, Any],
    static_dir: Path,
    preview_dir: Path | None = None,
    dry_runs: Any | None = None,
    applies: Any | None = None,
    initializer: Any | None = None,
    inventory_store: GroupInventoryStore | None = None,
    preview_gateway_factory: Any | None = None,
    codex_tasks: Any | None = None,
    host: str = "127.0.0.1",
    port: int = 8765,
    auth: DashboardAuth | None = None,
    job_queue: DurableJobQueue | None = None,
) -> DashboardServer:
    auth = auth or DashboardAuth()
    if host not in {"127.0.0.1", "localhost", "::1"} and not auth.enabled:
        raise ValueError("non-loopback dashboard requires a password or API token")
    server = DashboardServer((host, port), Handler)
    server.auth = auth
    server.job_queue = job_queue
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
    server.jobs_started_at = datetime.now(UTC)
    return server


def main(argv: list[str] | None = None) -> int:
    project_root = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(
        description="Serve the local SolutionRunner group dashboard"
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--db", type=Path, default=project_root / "var/dashboard/dashboard.sqlite3"
    )
    parser.add_argument("--var", type=Path, default=project_root / "var")
    parser.add_argument("--static", type=Path, default=project_root / "dashboard/dist")
    parser.add_argument(
        "--previews", type=Path, default=project_root / "var/dashboard/previews"
    )
    args = parser.parse_args(argv)
    auth = DashboardAuth(
        password=os.environ.get("SOLUTION_RUNNER_DASHBOARD_PASSWORD", ""),
        token=os.environ.get("SOLUTION_RUNNER_DASHBOARD_TOKEN", ""),
        username=os.environ.get("SOLUTION_RUNNER_DASHBOARD_USER", "owner"),
    )
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not auth.enabled:
        parser.error(
            "non-loopback dashboard requires SOLUTION_RUNNER_DASHBOARD_PASSWORD or SOLUTION_RUNNER_DASHBOARD_TOKEN"
        )

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
    print(
        f"Dashboard: {result['groups']} groups, {result['runs']} with runs, {result['warnings']} warnings"
    )
    print(f"Open on http://{args.host}:{args.port}")
    api_key = os.environ.get("TEACHERHELPER_MCP_API_KEY", "").strip()
    gateway_factory = lambda: JsonRpcMcpGateway(
        url=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
        api_key=api_key,
        timeout_seconds=45,
    )
    runner_executor = DurableJobQueue(args.db, args.var / "dashboard/logs")
    dry_runs = (
        DryRunManager(
            var_dir=args.var,
            profiles=profiles,
            gateway_factory=gateway_factory,
            store=store,
            inventory_store=inventory_store,
            on_complete=None,
            background_executor=runner_executor,
        )
        if api_key
        else None
    )
    applies = (
        ApplyManager(
            var_dir=args.var,
            profiles=profiles,
            inventory_store=inventory_store,
            store=store,
            background_executor=runner_executor,
        )
        if api_key
        else None
    )
    server: DashboardServer | None = None

    def on_dry_run_complete(group_key: str, state: Mapping[str, Any]) -> None:
        _finish_automatic_dry_run(store, group_key, state)
        group = store.get_group(group_key) or {}
        if (
            state.get("mode") == "all"
            and state.get("status") == "completed"
            and group.get("agent_status") == "updated"
        ):
            _refresh_server_profiles(server)

    if dry_runs is not None:
        dry_runs.on_complete = on_dry_run_complete

    def on_codex_exit(thread_id: str, code: int) -> None:
        _refresh_server_profiles(server)
        _handle_codex_exit(store, thread_id, code, dry_runs)

    if dry_runs is not None:
        runner_executor.register("dry-run", dry_runs.run_now)
    if applies is not None:
        runner_executor.register("apply-problem", applies.run_now)
        runner_executor.register("apply-group", applies.run_group_now)
        runner_executor.register("helpers", applies.run_helpers_now)

    codex_tasks = CodexTaskService(project_root=project_root, on_exit=on_codex_exit)

    initializer = (
        GroupInitializer(
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
        )
        if api_key
        else None
    )
    if dry_runs is not None:
        dry_runs.initializer = initializer
    server = make_server(
        store=store,
        var_dir=args.var,
        profiles=profiles,
        static_dir=args.static,
        preview_dir=args.previews,
        dry_runs=dry_runs,
        applies=applies,
        initializer=initializer,
        inventory_store=inventory_store,
        preview_gateway_factory=gateway_factory if api_key else None,
        codex_tasks=codex_tasks,
        host=args.host,
        port=args.port,
        auth=auth,
        job_queue=runner_executor,
    )
    runner_executor.start()
    Thread(
        target=_resume_automatic_groups,
        args=(store, inventory_store, codex_tasks),
        daemon=True,
    ).start()
    profile_watch_stop = Event()
    Thread(
        target=_watch_profile_sources,
        args=(server, project_root, profile_watch_stop),
        daemon=True,
    ).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        profile_watch_stop.set()
        server.server_close()
        runner_executor.shutdown(cancel_futures=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
