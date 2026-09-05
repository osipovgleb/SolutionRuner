"""Apply Helpers stage state only to fully verified polygon targets."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any

from .mcp_runtime import McpGateway
from .models import GroupProfile, ProblemStageResult
from .progress import ProgressReporter, TargetProgress


class HelpersRuntimeError(RuntimeError):
    """Report one target-local Helpers state or readback failure."""


def _desired_branches(profile: GroupProfile) -> dict[str, dict[str, Any]]:
    """Build fresh branch values from one immutable group profile."""

    branches = {
        branch: {"status": "ready", "revision": 2, "attempted_revision": 2}
        for branch in profile.helpers_ready_branches
    }
    branches.update(
        {
            branch: {
                "status": "not_required",
                "revision": 1,
                "attempted_revision": 1,
            }
            for branch in profile.helpers_not_required_branches
        }
    )
    return branches


def _desired_values(profile: GroupProfile) -> dict[str, Any]:
    """Return the exact database readback expected after Helpers completion."""

    return {
        "helpers_status": "ready",
        "helpers_json": {"schema_version": 2, **_desired_branches(profile)},
    }


def _helpers_state(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Extract current Helpers values and stale-write token."""

    details = payload.get("stage_details")
    tokens = payload.get("stage_state_tokens")
    values = details.get("helpers") if isinstance(details, dict) else None
    token = tokens.get("helpers") if isinstance(tokens, dict) else None
    if not isinstance(values, dict) or not isinstance(token, str) or not token:
        raise HelpersRuntimeError("pipeline state omitted Helpers values or token")
    return values, token


def _setter_readback(
    response: dict[str, Any],
    *,
    problem_id: str,
    expected_values: dict[str, Any],
) -> None:
    """Validate one single-target database readback from the setter."""

    results = response.get("results")
    if (
        response.get("stage") != "helpers"
        or int(response.get("requested_count") or 0) != 1
        or not isinstance(results, list)
        or len(results) != 1
    ):
        raise HelpersRuntimeError("Helpers setter returned an invalid summary")
    item = results[0]
    if (
        not isinstance(item, dict)
        or item.get("problem_id") != problem_id
        or item.get("read_from_database") is not True
        or item.get("values") != expected_values
    ):
        raise HelpersRuntimeError("Helpers setter readback differs from desired state")


def _eligible(result: ProblemStageResult, *, apply: bool) -> bool:
    """Return whether one verified upstream result may enter Helpers."""

    allowed = {"applied", "already_complete"} if apply else {"planned"}
    return result.stage == "solution_answer" and result.status in allowed


def _skipped_result(
    upstream: ProblemStageResult,
    profile: GroupProfile,
    reporter: ProgressReporter,
    progress: TargetProgress,
) -> ProblemStageResult:
    """Report and return one target rejected by the upstream gate."""

    reporter.task(
        profile.theme_title,
        profile.group_key,
        upstream.source_problem_id,
        progress,
        "HELPERS SKIPPED",
        severity="warning",
        stage="helpers",
        details={"upstream_stage": upstream.stage, "upstream_status": upstream.status},
    )
    return ProblemStageResult(
        problem_id=upstream.problem_id,
        source_problem_id=upstream.source_problem_id,
        stage="helpers",
        status="skipped",
        message=f"ineligible upstream {upstream.stage}:{upstream.status}",
    )


def _planned_result(
    upstream: ProblemStageResult,
    profile: GroupProfile,
    reporter: ProgressReporter,
    progress: TargetProgress,
) -> ProblemStageResult:
    """Report and return one dry-run Helpers result."""

    reporter.task(
        profile.theme_title,
        profile.group_key,
        upstream.source_problem_id,
        progress,
        "HELPERS PLANNED",
        severity="info",
        stage="helpers",
    )
    return ProblemStageResult(
        problem_id=upstream.problem_id,
        source_problem_id=upstream.source_problem_id,
        stage="helpers",
        status="planned",
    )


def _apply_target(
    gateway: McpGateway,
    upstream: ProblemStageResult,
    profile: GroupProfile,
    reporter: ProgressReporter,
    progress: TargetProgress,
    desired_values: dict[str, Any],
) -> ProblemStageResult:
    """Apply and reconcile Helpers state for one eligible target."""

    current, token = _helpers_state(
        gateway.get_problem_pipeline_state(upstream.problem_id)
    )
    status = "already_complete"
    if current != desired_values:
        update = {
            "problem_id": upstream.problem_id,
            "expected_stage_state_token": token,
            "values": {
                "operation": "set_branches",
                "branches": _desired_branches(profile),
            },
        }
        try:
            response = gateway.set_problem_pipeline_stage_state_batch(
                "helpers",
                [update],
                (
                    "Complete verified grid-polygon solution for "
                    f"{profile.theme_title} group {profile.group_key}"
                ),
            )
            _setter_readback(
                response,
                problem_id=upstream.problem_id,
                expected_values=desired_values,
            )
        except Exception:
            reconciled, _ = _helpers_state(
                gateway.get_problem_pipeline_state(upstream.problem_id)
            )
            if reconciled != desired_values:
                raise
        status = "applied"
    reporter.task(
        profile.theme_title,
        profile.group_key,
        upstream.source_problem_id,
        progress,
        "HELPERS READY",
        stage="helpers",
    )
    return ProblemStageResult(
        problem_id=upstream.problem_id,
        source_problem_id=upstream.source_problem_id,
        stage="helpers",
        status=status,
    )


def _failed_result(
    upstream: ProblemStageResult,
    profile: GroupProfile,
    reporter: ProgressReporter,
    progress: TargetProgress,
    exc: Exception,
) -> ProblemStageResult:
    """Report and return one isolated Helpers failure."""

    reporter.task(
        profile.theme_title,
        profile.group_key,
        upstream.source_problem_id,
        progress,
        "HELPERS FAILED",
        severity="error",
        stage="helpers",
        details={"exception_type": type(exc).__name__, "exception": str(exc)},
    )
    return ProblemStageResult(
        problem_id=upstream.problem_id,
        source_problem_id=upstream.source_problem_id,
        stage="helpers",
        status="failed",
        message=" ".join(str(exc).split())[:2000],
    )


def _run_isolated_target(
    gateway: McpGateway,
    profile: GroupProfile,
    reporter: ProgressReporter,
    apply: bool,
    desired_values: dict[str, Any],
    total: int,
    indexed_upstream: tuple[int, ProblemStageResult],
) -> ProblemStageResult:
    """Run one Helpers target while preserving its frozen progress index."""

    index, upstream = indexed_upstream
    progress = TargetProgress(index=index, total=total)
    if not _eligible(upstream, apply=apply):
        return _skipped_result(upstream, profile, reporter, progress)
    if not apply:
        return _planned_result(upstream, profile, reporter, progress)
    try:
        return _apply_target(
            gateway,
            upstream,
            profile,
            reporter,
            progress,
            desired_values,
        )
    except Exception as exc:  # noqa: BLE001 - exact target isolation is required.
        return _failed_result(upstream, profile, reporter, progress, exc)


def run_helpers_stage(
    gateway: McpGateway,
    solution_results: tuple[ProblemStageResult, ...],
    profile: GroupProfile,
    reporter: ProgressReporter,
    *,
    apply: bool,
    max_workers: int = 1,
) -> tuple[ProblemStageResult, ...]:
    """Apply Helpers state per verified target and isolate every failure."""

    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    if not solution_results:
        return ()
    desired_values = _desired_values(profile)
    indexed_results = tuple(enumerate(solution_results, start=1))
    run_target = partial(
        _run_isolated_target,
        gateway,
        profile,
        reporter,
        apply,
        desired_values,
        len(solution_results),
    )
    if max_workers == 1:
        return tuple(map(run_target, indexed_results))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return tuple(executor.map(run_target, indexed_results))
