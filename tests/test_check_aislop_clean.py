"""Test the exact AISlop report and suppression quality gate."""

from __future__ import annotations

from pathlib import Path

from scripts.check_aislop_clean import (
    parse_scan_output,
    suppression_errors,
    validate_report,
)


def healthy_report() -> dict[str, object]:
    """Return a literal score-100 report with every required engine active."""

    return {
        "scoreable": True,
        "score": 100,
        "diagnostics": [],
        "engines": {
            "format": {"issues": 0, "skipped": False},
            "lint": {"issues": 0, "skipped": False},
            "code-quality": {"issues": 0, "skipped": False},
            "ai-slop": {"issues": 0, "skipped": False},
            "security": {"issues": 0, "skipped": False},
            "architecture": {"issues": 0, "skipped": False},
        },
    }


def test_validate_report_accepts_exact_clean_scan() -> None:
    """Accept a scoreable zero-diagnostic report only when all engines ran."""

    assert validate_report(healthy_report()) == []


def test_validate_report_rejects_unscoreable_scan() -> None:
    """Reject a scan whose engines did not produce a score."""

    report = healthy_report()
    report["scoreable"] = False

    assert validate_report(report) == ["AISlop report is not scoreable"]


def test_validate_report_rejects_score_below_100() -> None:
    """Reject a rounded quality result below the exact repository target."""

    report = healthy_report()
    report["score"] = 99

    assert validate_report(report) == ["AISlop score must be 100 (got 99)"]


def test_validate_report_rejects_diagnostics() -> None:
    """Reject any diagnostic even when the aggregate score remains 100."""

    report = healthy_report()
    report["diagnostics"] = [{"severity": "warning", "message": "example"}]

    assert validate_report(report) == ["AISlop report contains 1 diagnostic"]


def test_validate_report_rejects_missing_engine() -> None:
    """Reject a report that silently omits the architecture engine."""

    report = healthy_report()
    engines = report["engines"]
    assert isinstance(engines, dict)
    engines.pop("architecture")

    assert validate_report(report) == ["AISlop report is missing engine: architecture"]


def test_validate_report_rejects_skipped_engine() -> None:
    """Reject an architecture engine that was configured but skipped."""

    report = healthy_report()
    engines = report["engines"]
    assert isinstance(engines, dict)
    engines["architecture"] = {"issues": 0, "skipped": True}

    assert validate_report(report) == ["AISlop engine was skipped: architecture"]


def test_validate_report_rejects_engine_issue_count() -> None:
    """Reject inconsistent reports that hide engine issues from diagnostics."""

    report = healthy_report()
    engines = report["engines"]
    assert isinstance(engines, dict)
    engines["lint"] = {"issues": 2, "skipped": False}

    assert validate_report(report) == ["AISlop engine lint reports 2 issues"]


def test_suppression_errors_reports_only_active_source(tmp_path: Path) -> None:
    """Reject suppression directives in source while ignoring vendored files."""

    directive = "aislop" + "-ignore lint"
    active_file = tmp_path / "src/example.py"
    active_file.parent.mkdir(parents=True)
    active_file.write_text(f"# {directive}\n", encoding="utf-8")
    vendored_file = tmp_path / "backend/.venv/example.py"
    vendored_file.parent.mkdir(parents=True)
    vendored_file.write_text(f"# {directive}\n", encoding="utf-8")

    assert suppression_errors(tmp_path) == [
        "src/example.py:1: AISlop suppression directives are forbidden",
    ]


def test_parse_scan_output_rejects_failed_command() -> None:
    """Preserve a failed AISlop command's stderr as the gate diagnostic."""

    report, errors = parse_scan_output(
        returncode=2,
        stdout="",
        stderr="configuration failed\n",
    )

    assert report is None
    assert errors == ["AISlop scan failed with exit code 2: configuration failed"]


def test_parse_scan_output_rejects_malformed_json() -> None:
    """Reject scanner output that cannot be interpreted as a JSON report."""

    report, errors = parse_scan_output(
        returncode=0,
        stdout="not-json",
        stderr="",
    )

    assert report is None
    assert errors == ["AISlop scan did not return valid JSON"]



def test_parse_scan_output_accepts_report_with_nonzero_exit() -> None:
    """A scan with findings still returns a report for validation."""
    report, errors = parse_scan_output(returncode=1, stdout='{"score": 83}', stderr="")
    assert report == {"score": 83}
    assert errors == []
