"""Keep launcher stdout/stderr without redirecting the server's global streams."""

from contextvars import ContextVar
from datetime import UTC, datetime
import os
from pathlib import Path
import subprocess
from typing import Sequence
from uuid import uuid4


job_log: ContextVar[Path | None] = ContextVar("dashboard_job_log", default=None)


def run_logged(command: Sequence[str]) -> int:
    path = job_log.get()
    if path is None:
        root = Path(__file__).resolve().parents[3]
        path = root / "var/dashboard/logs" / f"launcher-{datetime.now(UTC):%Y%m%dT%H%M%S}-{uuid4().hex}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as output:
        return subprocess.run(command, env=os.environ.copy(), stdout=output,
                              stderr=subprocess.STDOUT, check=False).returncode
