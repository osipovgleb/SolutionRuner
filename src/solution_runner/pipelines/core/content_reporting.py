"""Persist and report content-rule progress without solution content."""

import json
from pathlib import Path
from typing import Any

from ..grid_polygon.progress import ProgressReporter, TargetProgress
from .models import GroupProfile, ProblemStageResult


def _summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build one content-free application summary from frozen-order results."""

    return {
        "applied_count": sum(item["status"] == "applied" for item in results),
        "already_complete_count": sum(
            item["status"] == "already_complete" for item in results
        ),
        "blocked_count": sum(item["status"] == "blocked" for item in results),
        "failed_count": sum(item["status"] == "failed" for item in results),
        "results": results,
    }


def _write_checkpoint(path: Path, summary: dict[str, Any]) -> None:
    """Atomically replace one local apply checkpoint after a completed batch."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _report_content_result(
    reporter: ProgressReporter,
    profile: GroupProfile,
    result: dict[str, Any],
    progress: TargetProgress,
) -> ProblemStageResult:
    """Emit old-pipeline milestones and project one content result."""

    status = str(result.get("status") or "failed")
    source_problem_id = str(result.get("source_problem_id") or "")
    problem_id = str(result.get("problem_id") or "")
    message = str(result.get("message") or "") or None
    if status == "applied":
        solution_action, answer_action, severity = (
            "SOLUTION WRITTEN",
            "ANSWER VERIFIED",
            "success",
        )
        stage_status = "applied"
    elif status == "already_complete":
        solution_action, answer_action, severity = (
            "SOLUTION ALREADY COMPLETE",
            "ANSWER VERIFIED",
            "success",
        )
        stage_status = "already_complete"
    elif status == "planned":
        solution_action, answer_action, severity = (
            "SOLUTION PLANNED",
            "ANSWER PLANNED",
            "info",
        )
        stage_status = "planned"
    else:
        solution_action, answer_action, severity = (
            "SOLUTION FAILED",
            "ANSWER SKIPPED",
            "error",
        )
        stage_status = "failed"
    details = {"message": message} if message else None
    reporter.task(
        profile.theme_title,
        profile.group_key,
        source_problem_id,
        progress,
        solution_action,
        severity=severity,
        stage="solution",
        details=details,
    )
    reporter.task(
        profile.theme_title,
        profile.group_key,
        source_problem_id,
        progress,
        answer_action,
        severity=severity,
        stage="answer",
        details=details,
    )
    return ProblemStageResult(
        problem_id=problem_id,
        source_problem_id=source_problem_id,
        stage="solution_answer",
        status=stage_status,
        message=message,
    )
