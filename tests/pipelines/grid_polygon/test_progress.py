"""Protect compact progress and detailed internal diagnostics."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from io import StringIO
import json
import threading
import time

from solution_runner.pipelines.grid_polygon.progress import ProgressReporter, TargetProgress


def test_solution_and_answer_share_frozen_target_progress() -> None:
    """Show the same target position on both requested solution milestones."""

    console = StringIO()
    reporter = ProgressReporter(console=console, internal=StringIO(), color=False)
    progress = TargetProgress(index=241, total=251)

    reporter.task("Треугольник", "27548", "247927", progress, "SOLUTION WRITTEN")
    reporter.task("Треугольник", "27548", "247927", progress, "ANSWER VERIFIED")

    lines = console.getvalue().splitlines()
    assert len(lines) == 2
    assert "[241/251]" in lines[0]
    assert "[241/251]" in lines[1]
    assert "SOLUTION WRITTEN" in lines[0]
    assert "ANSWER VERIFIED" in lines[1]


def test_failure_and_skip_consume_progress_without_console_details() -> None:
    """Keep console compact while preserving error evidence internally."""

    console = StringIO()
    internal = StringIO()
    reporter = ProgressReporter(console=console, internal=internal, color=False)

    reporter.task(
        "Треугольник",
        "27548",
        "247927",
        TargetProgress(241, 251),
        "SOLUTION FAILED",
        severity="error",
        details={"exception": "coordinate formula mismatch", "sha256": "abc"},
    )
    reporter.task(
        "Треугольник",
        "27548",
        "247929",
        TargetProgress(242, 251),
        "SKIPPED",
        severity="warning",
    )

    lines = console.getvalue().splitlines()
    assert "[241/251]" in lines[0] and "[242/251]" in lines[1]
    assert "coordinate formula mismatch" not in console.getvalue()
    records = [json.loads(line) for line in internal.getvalue().splitlines()]
    assert records[0]["details"]["exception"] == "coordinate formula mismatch"
    assert records[0]["progress"] == {"index": 241, "total": 251}


def test_color_restores_identity_and_action_palette() -> None:
    """Render theme/group blue, task yellow, and successful action green."""

    console = StringIO()
    reporter = ProgressReporter(console=console, internal=StringIO(), color=True)
    reporter.task(
        "Треугольник",
        "27548",
        "247927",
        TargetProgress(1, 2),
        "ANSWER VERIFIED",
    )

    line = console.getvalue()
    assert "\x1b[34mТреугольник / group 27548\x1b[0m" in line
    assert "\x1b[33mTask 247927\x1b[0m" in line
    assert "[1/2]" in line
    assert "\x1b[32mANSWER VERIFIED\x1b[0m" in line


class OverlapDetectingStream(StringIO):
    """Detect concurrent write calls while retaining their text."""

    def __init__(self) -> None:
        """Initialize synchronized overlap counters."""

        super().__init__()
        self._state_lock = threading.Lock()
        self._active = 0
        self.overlaps = 0

    def write(self, value: str) -> int:
        """Yield during writes so missing reporter serialization is observable."""

        with self._state_lock:
            self._active += 1
            if self._active > 1:
                self.overlaps += 1
        time.sleep(0.01)
        try:
            return super().write(value)
        finally:
            with self._state_lock:
                self._active -= 1


def test_parallel_progress_writes_are_serialized_per_milestone() -> None:
    """Keep each console/internal milestone atomic across worker threads."""

    console = OverlapDetectingStream()
    internal = OverlapDetectingStream()
    reporter = ProgressReporter(console=console, internal=internal, color=False)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                reporter.task,
                "Треугольник",
                "27548",
                str(source_id),
                TargetProgress(index, 2),
                "SOLUTION WRITTEN",
            )
            for index, source_id in enumerate(("1", "2"), start=1)
        ]
        for future in futures:
            future.result()

    assert console.overlaps == 0
    assert internal.overlaps == 0
    assert len(console.getvalue().splitlines()) == 2
    assert len(internal.getvalue().splitlines()) == 2
