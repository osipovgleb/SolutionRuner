from pathlib import Path

import pytest

from solution_runner.dashboard.cli import parse_dashboard_args


def test_remote_dashboard_requires_authentication(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("SOLUTION_RUNNER_DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("SOLUTION_RUNNER_DASHBOARD_TOKEN", raising=False)
    with pytest.raises(SystemExit):
        parse_dashboard_args(["--host", "0.0.0.0"], tmp_path)


def test_remote_dashboard_accepts_token_and_project_defaults(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("SOLUTION_RUNNER_DASHBOARD_TOKEN", "test-token")
    args, auth = parse_dashboard_args(["--host", "0.0.0.0"], tmp_path)
    assert auth.enabled
    assert args.db == tmp_path / "var/dashboard/dashboard.sqlite3"
    assert args.static == tmp_path / "dashboard/dist"
