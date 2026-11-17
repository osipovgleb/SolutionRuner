#!/usr/bin/env python3
"""Require an exact-clean AISlop scan with every repository engine active."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
import subprocess


REQUIRED_ENGINES = {
    "format",
    "lint",
    "code-quality",
    "ai-slop",
    "security",
    "architecture",
}
SOURCE_ROOTS = ("src", "tests", "scripts", "dashboard", "codex-runtime", "experiments")
SOURCE_SUFFIXES = {".js", ".mjs", ".py", ".sh", ".sql", ".ts", ".tsx"}
IGNORED_PARTS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "generated",
    "graphify-out",
    "node_modules",
    "out",
    "output",
}
SUPPRESSION_MARKER = "aislop" + "-ignore"
ROOT = Path(__file__).resolve().parents[1]


def validate_report(report: object) -> list[str]:
    """Return invariant violations found in one parsed AISlop JSON report."""

    if not isinstance(report, Mapping):
        return ["AISlop report must be a JSON object"]

    errors: list[str] = []
    if report.get("scoreable") is not True:
        errors.append("AISlop report is not scoreable")
    if report.get("score") != 100:
        errors.append(f"AISlop score must be 100 (got {report.get('score')})")

    diagnostics = report.get("diagnostics")
    if not isinstance(diagnostics, list):
        errors.append("AISlop report diagnostics must be a JSON array")
    elif diagnostics:
        noun = "diagnostic" if len(diagnostics) == 1 else "diagnostics"
        errors.append(f"AISlop report contains {len(diagnostics)} {noun}")

    engines = report.get("engines")
    if not isinstance(engines, Mapping):
        errors.append("AISlop report engines must be a JSON object")
        return errors

    for engine_name in sorted(REQUIRED_ENGINES):
        engine = engines.get(engine_name)
        if not isinstance(engine, Mapping):
            errors.append(f"AISlop report is missing engine: {engine_name}")
            continue
        if engine.get("skipped") is True:
            errors.append(f"AISlop engine was skipped: {engine_name}")
        issue_count = engine.get("issues")
        if issue_count != 0:
            errors.append(f"AISlop engine {engine_name} reports {issue_count} issues")
    return errors


def suppression_errors(root: Path) -> list[str]:
    """Return active source locations containing AISlop suppression directives."""

    errors: list[str] = []
    for relative_root in SOURCE_ROOTS:
        source_root = root / relative_root
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*")):
            if (
                not path.is_file()
                or path.suffix not in SOURCE_SUFFIXES
                or any(part in IGNORED_PARTS for part in path.relative_to(root).parts)
            ):
                continue
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                if SUPPRESSION_MARKER in line:
                    errors.append(
                        f"{path.relative_to(root)}:{line_number}: "
                        "AISlop suppression directives are forbidden"
                    )
    return errors


def parse_scan_output(
    *,
    returncode: int,
    stdout: str,
    stderr: str,
) -> tuple[object | None, list[str]]:
    """Parse one completed AISlop process into a report or stable errors."""

    try:
        report = json.loads(stdout)
    except json.JSONDecodeError:
        if returncode != 0:
            detail = stderr.strip() or stdout.strip() or "no diagnostic output"
            return None, [f"AISlop scan failed with exit code {returncode}: {detail}"]
        return None, ["AISlop scan did not return valid JSON"]
    return report, []


def main() -> int:
    """Run the pinned scanner against the current checkout."""

    completed = subprocess.run(
        ("npx", "--no-install", "aislop", "scan", "--json", str(ROOT)),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report, errors = parse_scan_output(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if report is not None:
        errors.extend(validate_report(report))
    errors.extend(suppression_errors(ROOT))
    if errors:
        print("AISlop exact-clean check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("AISlop exact-clean check passed: 100/100, 0 diagnostics, 6 engines active.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
