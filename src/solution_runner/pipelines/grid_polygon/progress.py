"""Emit compact task progress and detailed machine-readable run evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import threading
from typing import Callable, Literal, Mapping, TextIO


Severity = Literal["info", "success", "warning", "error"]
_COLORS: dict[Severity, str] = {
    "info": "\033[36m",
    "success": "\033[32m",
    "warning": "\033[33m",
    "error": "\033[31m",
}
_IDENTITY_COLOR = "\033[34m"
_TASK_COLOR = "\033[33m"
_RESET = "\033[0m"


@dataclass(frozen=True)
class TargetProgress:
    """Identify one target's stable one-based position in a frozen run."""

    index: int
    total: int

    def __post_init__(self) -> None:
        """Reject progress pairs that cannot identify a frozen target."""

        if self.total <= 0 or self.index <= 0 or self.index > self.total:
            raise ValueError("target progress must satisfy 1 <= index <= total")


class ProgressReporter:
    """Write short console milestones and rich JSONL diagnostics separately."""

    def __init__(
        self,
        *,
        console: TextIO,
        internal: TextIO,
        color: bool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Bind output sinks without owning their lifecycle."""

        self._console = console
        self._internal = internal
        self._color = color
        self._clock = clock or datetime.now
        self._write_lock = threading.Lock()

    def group(
        self,
        theme_title: str,
        group_key: str,
        action: str,
        *,
        severity: Severity = "info",
        stage: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        """Emit one group-level milestone before task progress is available."""

        with self._write_lock:
            timestamp = self._clock().strftime("%H:%M:%S")
            action_text = (
                f"{_COLORS[severity]}{action}{_RESET}" if self._color else action
            )
            identity = f"{theme_title} / group {group_key}"
            identity_text = (
                f"{_IDENTITY_COLOR}{identity}{_RESET}" if self._color else identity
            )
            self._console.write(f"{timestamp}  {identity_text}  {action_text}\n")
            self._console.flush()
            record = {
                "timestamp": timestamp,
                "theme_title": theme_title,
                "group_key": group_key,
                "source_problem_id": None,
                "progress": None,
                "action": action,
                "severity": severity,
                "stage": stage,
                "details": dict(details or {}),
            }
            self._internal.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            )
            self._internal.flush()

    def task(
        self,
        theme_title: str,
        group_key: str,
        source_problem_id: str,
        progress: TargetProgress,
        action: str,
        *,
        severity: Severity = "success",
        stage: str | None = None,
        details: Mapping[str, object] | None = None,
    ) -> None:
        """Emit one stable task milestone to both configured sinks."""

        with self._write_lock:
            timestamp = self._clock().strftime("%H:%M:%S")
            action_text = (
                f"{_COLORS[severity]}{action}{_RESET}" if self._color else action
            )
            identity = f"{theme_title} / group {group_key}"
            identity_text = (
                f"{_IDENTITY_COLOR}{identity}{_RESET}" if self._color else identity
            )
            task = f"Task {source_problem_id}"
            task_text = f"{_TASK_COLOR}{task}{_RESET}" if self._color else task
            self._console.write(
                f"{timestamp}  {identity_text}  "
                f"{task_text}  [{progress.index}/{progress.total}]  "
                f"{action_text}\n"
            )
            self._console.flush()
            record = {
                "timestamp": timestamp,
                "theme_title": theme_title,
                "group_key": group_key,
                "source_problem_id": source_problem_id,
                "progress": {"index": progress.index, "total": progress.total},
                "action": action,
                "severity": severity,
                "stage": stage,
                "details": dict(details or {}),
            }
            self._internal.write(
                json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            )
            self._internal.flush()
