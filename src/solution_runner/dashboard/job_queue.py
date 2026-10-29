"""Durable serial runner queue; interrupted writes are never replayed."""

from concurrent.futures import Executor, Future, ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
import fcntl
import json
from pathlib import Path
import sqlite3
import traceback
from threading import Lock
from typing import Any, Callable

from .process_logs import job_log


def _now() -> str:
    return datetime.now(UTC).isoformat()


class DurableJobQueue(Executor):
    def __init__(self, database: Path, log_dir: Path | None = None) -> None:
        database.parent.mkdir(parents=True, exist_ok=True)
        self.database = database
        self.log_dir = log_dir or database.parent / "logs"
        self._file = database.with_suffix(database.suffix + ".runner.lock").open("a")
        try:
            fcntl.flock(self._file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._file.close()
            raise RuntimeError("another dashboard runner owns this database") from None
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="dashboard-run")
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._lock = Lock()
        self._started = False
        self._closed = False
        with self._connect() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS dashboard_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL, payload TEXT NOT NULL,
                status TEXT NOT NULL, created_at TEXT NOT NULL,
                started_at TEXT, finished_at TEXT, error TEXT
            )""")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.database, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def register(self, kind: str, handler: Callable[..., Any]) -> None:
        if self._started or kind in self._handlers:
            raise RuntimeError("register unique handlers before starting the queue")
        self._handlers[kind] = handler

    def _fail_state(self, kind: str, payload: dict[str, Any], error: str) -> None:
        handler = self._handlers.get(kind)
        if handler is None:
            return
        manager = handler.__self__
        group_key = str(payload["args"][0])
        state = manager.get(group_key)
        if state and state.get("status") in {"queued", "running", "retry_wait"}:
            manager._write({**state, "status": "failed", "error": error, "finished_at": _now()})
        store = manager.store
        if store is not None and kind == "dry-run" and payload["args"][1] == "all":
            store.update_group(group_key, {"full_dry_run_status": "failed"})

    def start(self) -> None:
        with self._lock:
            if self._started or self._closed:
                raise RuntimeError("queue already started or closed")
            with self._connect() as connection:
                interrupted = connection.execute(
                    "SELECT * FROM dashboard_jobs WHERE status='running' ORDER BY id"
                ).fetchall()
                connection.execute(
                    "UPDATE dashboard_jobs SET status='interrupted', finished_at=?, error=? WHERE status='running'",
                    (_now(), "Dashboard stopped during execution; inspect results before retrying"),
                )
                queued = connection.execute(
                    "SELECT * FROM dashboard_jobs WHERE status='queued' ORDER BY id"
                ).fetchall()
            for row in interrupted:
                self._fail_state(row["kind"], json.loads(row["payload"]),
                                 "Execution interrupted; inspect external results before retrying")
            # Legacy JSON state can predate the durable queue or a process can
            # stop between writing the UI state and committing a queue entry.
            pending = {(row["kind"], str(json.loads(row["payload"])["args"][0])) for row in queued}
            managers = {handler.__self__ for handler in self._handlers.values()}
            for manager in managers:
                state_dir = getattr(manager, "state_dir", None)
                if state_dir is None:
                    continue
                manager_kinds = {kind for kind, handler in self._handlers.items() if handler.__self__ is manager}
                for path in state_dir.glob("*.json"):
                    state = manager.get(path.stem)
                    if not state or state.get("status") not in {"queued", "running", "retry_wait"}:
                        continue
                    if not any((kind, path.stem) in pending for kind in manager_kinds):
                        kind = "dry-run" if "dry-run" in manager_kinds else "apply-group"
                        self._fail_state(kind, {"args": [path.stem, state.get("mode")]},
                                         "No durable job exists; inspect results before retrying")
            self._started = True
            for row in queued:
                if row["kind"] not in self._handlers:
                    continue  # Missing MCP credentials: retain work until a configured restart.
                self._pool.submit(self._run, row["id"], row["kind"], json.loads(row["payload"]), True)

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Future:
        with self._lock:
            if not self._started or self._closed:
                raise RuntimeError("queue is not running")
            kind = next((key for key, handler in self._handlers.items() if handler == fn), None)
            if kind is None:
                raise ValueError("unregistered job handler")
            payload = {"args": args, "kwargs": kwargs}
            def encode(value: Any) -> Any:
                if isinstance(value, (set, frozenset)):
                    return sorted(value)
                raise TypeError(f"unsupported job value: {type(value).__name__}")
            encoded = json.dumps(payload, default=encode)
            with self._connect() as connection:
                cursor = connection.execute(
                    "INSERT INTO dashboard_jobs(kind,payload,status,created_at) VALUES (?,?,'queued',?)",
                    (kind, encoded, _now()),
                )
                job_id = cursor.lastrowid
            return self._pool.submit(self._run, job_id, kind, json.loads(encoded), False)

    def _run(self, job_id: int, kind: str, payload: dict[str, Any], recovered: bool) -> Any:
        with self._connect() as connection:
            connection.execute("UPDATE dashboard_jobs SET status='running', started_at=? WHERE id=?", (_now(), job_id))
        token = job_log.set(self.log_dir / f"job-{job_id}.log")
        try:
            handler = self._handlers[kind]
            # Re-check approval at execution time, including after a restart.
            manager = handler.__self__
            if kind == "apply-group":
                manager._verified_group(payload["args"][0])
            elif kind == "apply-problem":
                manager._verified_row(*payload["args"][:2])
            result = handler(*payload["args"], **payload["kwargs"])
            if recovered and kind == "dry-run" and manager.on_complete:
                manager.on_complete(payload["args"][0], result)
            status = "failed" if isinstance(result, dict) and result.get("status") == "failed" else "completed"
            error = result.get("error") if isinstance(result, dict) else None
        except Exception as exc:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            with (self.log_dir / f"job-{job_id}.log").open("a", encoding="utf-8") as output:
                traceback.print_exc(file=output)
            self._fail_state(kind, payload, str(exc))
            with self._connect() as connection:
                connection.execute("UPDATE dashboard_jobs SET status='failed', finished_at=?, error=? WHERE id=?", (_now(), str(exc), job_id))
            raise
        finally:
            job_log.reset(token)
        with self._connect() as connection:
            connection.execute("UPDATE dashboard_jobs SET status=?, finished_at=?, error=? WHERE id=?", (status, _now(), error, job_id))
        return result

    def list_jobs(self, limit: int = 100, group_key: str | None = None) -> list[dict[str, Any]]:
        with self._connect() as connection:
            if group_key is None:
                rows = connection.execute("SELECT * FROM dashboard_jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM dashboard_jobs WHERE json_extract(payload,'$.args[0]')=? ORDER BY id DESC LIMIT ?",
                    (group_key, limit),
                ).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]

    def log_tail(self, job_id: int) -> str:
        if not 0 < job_id < 2**63:
            raise KeyError(job_id)
        with self._connect() as connection:
            if connection.execute("SELECT id FROM dashboard_jobs WHERE id=?", (job_id,)).fetchone() is None:
                raise KeyError(job_id)
        path = self.log_dir / f"job-{job_id}.log"
        if not path.exists():
            return ""
        with path.open("rb") as stream:
            stream.seek(max(0, path.stat().st_size - 65536))
            return stream.read(65536).decode("utf-8", errors="replace")

    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None:
        if not wait:
            raise ValueError("durable queue must finish its running job before releasing ownership")
        with self._lock:
            self._closed = True
        self._pool.shutdown(wait=True, cancel_futures=cancel_futures)
        self._file.close()
