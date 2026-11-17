"""Parse dashboard command-line options and validate access settings."""

import argparse
import os
from pathlib import Path

from .auth import DashboardAuth


def parse_dashboard_args(argv: list[str] | None, project_root: Path):
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

    return args, auth
