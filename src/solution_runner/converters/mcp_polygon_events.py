"""Emit structured and human-readable asset pipeline events."""

from __future__ import annotations

import json
import os
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ANSI_RESET = "\033[0m"

ANSI_BOLD = "\033[1m"

ANSI_RED = "\033[31m"

ANSI_GREEN = "\033[32m"

ANSI_YELLOW = "\033[33m"

ANSI_BLUE = "\033[34m"

ANSI_MAGENTA = "\033[35m"

ANSI_CYAN = "\033[36m"

ANSI_BRIGHT_GREEN = "\033[92m"

TASK_STAGE_STYLES = {
    "source_downloaded": ("DOWNLOADED", ANSI_BLUE),
    "asset_prepared": ("CONVERTED", ANSI_MAGENTA),
    "upload_link_created": ("UPLOAD URL READY", ANSI_CYAN),
    "svg_uploaded": ("SVG UPLOADED", ANSI_GREEN),
    "asset_replaced": ("TRANSFORMATION APPLIED", ANSI_BRIGHT_GREEN),
    "asset_rolled_back": ("TRANSFORMATION ROLLED BACK", ANSI_BRIGHT_GREEN),
    "rollback_stale": ("SKIPPED / CHANGED", ANSI_YELLOW),
    "asset_rejected": ("REJECTED", ANSI_YELLOW),
    "asset_stale": ("SKIPPED / STALE", ANSI_YELLOW),
    "asset_error": ("ERROR", ANSI_RED),
}


class EventLogger:
    """Write flush-on-event JSONL plus compact human-readable stdout lines."""

    def __init__(self, path: Path, *, color: str = "auto") -> None:
        """Open an append-only log at *path*."""

        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._stream = path.open("a", encoding="utf-8")
        self._lock = threading.RLock()
        self._color = color == "always" or (
            color == "auto" and sys.stdout.isatty() and "NO_COLOR" not in os.environ
        )

    def close(self) -> None:
        """Flush and close the event stream."""

        with self._lock:
            self._stream.flush()
            self._stream.close()

    def emit(self, event: str, *, level: str = "info", **fields: Any) -> None:
        """Persist one structured event and mirror its key fields to stdout."""

        with self._lock:
            self._emit_unlocked(event, level=level, **fields)

    def _emit_unlocked(
        self,
        event: str,
        *,
        level: str = "info",
        **fields: Any,
    ) -> None:
        """Write one event while the logger lock is held."""

        payload = {
            "at": datetime.now(UTC).isoformat(),
            "level": level,
            "event": event,
            **fields,
        }
        line = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        self._stream.write(line + "\n")
        self._stream.flush()
        prefix = payload["at"][11:19]
        handlers = {
            "worklist_group_scan_start": self._display_worklist_group_scan_start,
            "worklist_group_scanned": self._display_worklist_group_scanned,
            "worklist_ready": self._display_worklist_ready,
            "resume_ready": self._display_resume_ready,
            "rollback_ready": self._display_rollback_ready,
            "group_transition": self._display_group_transition,
            "group_opened": self._display_group_opened,
            "batch_start": self._display_batch_start,
            "worker_pool_start": self._display_worker_pool_start,
            "batch_complete": self._display_batch_complete,
            "batch_pause": self._display_batch_pause,
            "run_complete": self._display_run_complete,
        }
        handler = handlers.get(event)
        if handler is not None:
            handler(prefix, fields)
            return
        if event in TASK_STAGE_STYLES and fields.get("source_problem_id"):
            label, stage_color = TASK_STAGE_STYLES[event]
            theme = str(fields.get("theme") or "unknown theme")
            group_key = str(fields.get("group_key") or "unknown")
            source_problem_id = str(fields["source_problem_id"])
            group_text = self._paint(
                f"{theme} / group {group_key}", ANSI_BOLD + ANSI_CYAN
            )
            task_text = self._paint(
                f"Task {source_problem_id}", ANSI_BOLD + ANSI_YELLOW
            )
            stage_text = self._paint(label, ANSI_BOLD + stage_color)
            detail = ""
            if event in {
                "asset_rejected",
                "asset_stale",
                "asset_error",
                "rollback_stale",
            }:
                reason = str(fields.get("reason") or "")
                detail = f"  {reason}" if reason else ""
            self._display(f"{prefix}  {group_text}  {task_text}  {stage_text}{detail}")
            return
        if event == "run_failed" or level.lower() == "error":
            reason = str(fields.get("reason") or event)
            message = f"ОШИБКА  {reason}"
            self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}")

    def _display_worklist_group_scan_start(
        self, prefix: str, fields: dict[str, Any]
    ) -> None:
        position = int(fields.get("position") or 0)
        total = int(fields.get("total_groups") or 0)
        theme = str(fields.get("theme") or "unknown theme")
        group_key = str(fields.get("group_key") or "unknown")
        message = f"СКАНИРУЮ ГРУППУ {position}/{total}  {theme} / {group_key}"
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_CYAN)}")

    def _display_worklist_group_scanned(
        self, prefix: str, fields: dict[str, Any]
    ) -> None:
        position = int(fields.get("position") or 0)
        total = int(fields.get("total_groups") or 0)
        theme = str(fields.get("theme") or "unknown theme")
        group_key = str(fields.get("group_key") or "unknown")
        tasks = int(fields.get("tasks") or 0)
        message = (
            f"ГРУППА ПРОСКАНИРОВАНА {position}/{total}  "
            f"{theme} / {group_key}  ЦЕЛЕЙ {tasks}"
        )
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_GREEN)}")

    def _display_worklist_ready(self, prefix: str, fields: dict[str, Any]) -> None:
        groups = int(fields.get("groups") or 0)
        tasks = int(fields.get("tasks") or 0)
        message = f"СПИСОК ЦЕЛЕЙ ГОТОВ  ГРУПП {groups}  ЗАДАЧ {tasks}"
        self._display(
            f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}"
        )

    def _display_resume_ready(self, prefix: str, fields: dict[str, Any]) -> None:
        tasks = int(fields.get("tasks") or 0)
        applied = int(fields.get("applied") or 0)
        missing = int(fields.get("missing") or 0)
        rejected = int(fields.get("rejected") or 0)
        message = (
            f"ВОЗОБНОВЛЕНИЕ: ОСТАЛОСЬ {tasks}  "
            f"ГОТОВЫХ ПРОПУЩЕНО {applied}  "
            f"НЕТ ФАЙЛА {missing}  REJECTED {rejected}"
        )
        self._display(
            f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}"
        )

    def _display_rollback_ready(self, prefix: str, fields: dict[str, Any]) -> None:
        tasks = int(fields.get("tasks") or 0)
        message = f"ROLLBACK ГОТОВ  ТОЧНЫХ ЦЕЛЕЙ {tasks}"
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}")

    def _display_group_transition(self, prefix: str, fields: dict[str, Any]) -> None:
        theme = str(fields.get("theme") or "unknown theme")
        group_key = str(fields.get("group_key") or "unknown")
        message = f"ПЕРЕХОЖУ К ГРУППЕ {theme} / {group_key}"
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}")

    def _display_group_opened(self, prefix: str, fields: dict[str, Any]) -> None:
        tasks = int(fields.get("tasks") or 0)
        message = f"ГРУППА ОТКРЫТА, ЦЕЛЕЙ {tasks}"
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_RED)}")

    def _display_batch_start(self, prefix: str, fields: dict[str, Any]) -> None:
        batch = int(fields.get("batch") or 0)
        tasks = int(fields.get("tasks") or 0)
        message = f"ПАКЕТ {batch}  ЗАДАЧ {tasks}"
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BLUE)}")

    def _display_worker_pool_start(self, prefix: str, fields: dict[str, Any]) -> None:
        tasks = int(fields.get("tasks") or 0)
        workers = int(fields.get("max_workers") or 0)
        message = f"ОКНО ЗАПУЩЕНО  ЗАДАЧ {tasks}  ПАРАЛЛЕЛЬНО {workers}"
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BLUE)}")

    def _display_batch_complete(self, prefix: str, fields: dict[str, Any]) -> None:
        batch = int(fields.get("batch") or 0)
        prepared = int(fields.get("prepared") or 0)
        replaced = int(fields.get("replaced") or 0)
        rolled_back = int(fields.get("rolled_back") or 0)
        if "rolled_back" in fields:
            message = f"ПАКЕТ {batch} ЗАВЕРШЁН  ОТКАЧЕНО {rolled_back}"
        else:
            message = (
                f"ПАКЕТ {batch} ЗАВЕРШЁН  "
                f"ПЕРЕФОРМАТИРОВАНО {prepared}  ПРИМЕНЕНО {replaced}"
            )
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_GREEN)}")

    def _display_batch_pause(self, prefix: str, fields: dict[str, Any]) -> None:
        seconds = fields.get("seconds") or 0
        message = f"ПАУЗА {seconds} СЕК."
        self._display(f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_YELLOW)}")

    def _display_run_complete(self, prefix: str, fields: dict[str, Any]) -> None:
        status = str(fields.get("status") or "completed")
        if "assets_rolled_back" in fields:
            rolled_back = int(fields.get("assets_rolled_back") or 0)
            errors = int(fields.get("asset_errors") or 0)
            message = (
                f"ROLLBACK ГОТОВ  {status}  ОТКАЧЕНО {rolled_back}  ОШИБОК {errors}"
            )
            self._display(
                f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}"
            )
            return
        replaced = int(fields.get("assets_replaced") or 0)
        rejected = int(fields.get("assets_rejected") or 0)
        errors = int(fields.get("asset_errors") or 0)
        message = (
            f"ГОТОВО  {status}  ПРИМЕНЕНО {replaced}  "
            f"ОТКЛОНЕНО {rejected}  ОШИБОК {errors}"
        )
        self._display(
            f"{prefix}  {self._paint(message, ANSI_BOLD + ANSI_BRIGHT_GREEN)}"
        )
        return

    def _display(self, message: str) -> None:
        """Write one progress line immediately to the active output stream."""
        sys.stdout.write(message + "\n")
        sys.stdout.flush()

    def _paint(self, text: str, style: str) -> str:
        """Wrap text in ANSI style codes when color output is enabled."""

        return f"{style}{text}{ANSI_RESET}" if self._color else text
