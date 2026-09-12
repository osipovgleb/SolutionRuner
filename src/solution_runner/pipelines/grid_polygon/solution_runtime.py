"""Execute reusable polygon solution plans with target-local isolation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
import hashlib
import re
from typing import Any, Protocol

from .mcp_runtime import McpGateway
from ..core.models import (
    GeometryAnalysis,
    GroupProfile,
    PreparedFigure,
    ProblemStageResult,
    SolutionDiagramSpec,
)
from .progress import ProgressReporter, TargetProgress
from .solution_plan import (
    AnswerVerificationError,
    SOLUTION_ASSET_KEY,
    SolutionPlan,
    SolutionRuntimeError,
    build_solution_plan,
    content_matches_plan,
    existing_solution_asset,
    normalized_content,
    verify_solution_plan,
)
from .strategies.protocol import SolutionStrategy


class SolutionGateway(McpGateway, Protocol):
    """Name the exact gateway operations consumed by this runtime."""


@dataclass(frozen=True)
class _SolutionContext:
    """Carry immutable dependencies shared by every frozen solution target."""

    gateway: SolutionGateway
    profile: GroupProfile
    strategy: SolutionStrategy
    reporter: ProgressReporter
    apply: bool
    total: int


def _diagram_specs(
    context: _SolutionContext,
    target: PreparedFigure,
    analysis: GeometryAnalysis,
) -> tuple[SolutionDiagramSpec, ...]:
    """Return explicit strategy diagrams with a legacy one-diagram adapter."""

    renderer = getattr(context.strategy, "render_solution_diagrams", None)
    if callable(renderer):
        diagrams = tuple(renderer(target, analysis, context.profile))
    elif context.strategy.requires_solution_diagram:
        diagrams = (
            SolutionDiagramSpec(
                asset_key=SOLUTION_ASSET_KEY,
                solution_variant_index=0,
                svg_bytes=context.strategy.render_solution_svg(target, analysis),
                alt_text=str(list(target.coordinates)),
            ),
        )
    else:
        diagrams = ()
    keys = [diagram.asset_key for diagram in diagrams]
    if len(keys) != len(set(keys)) or any(
        not key or diagram.solution_variant_index < 0
        for key, diagram in zip(keys, diagrams, strict=True)
    ):
        raise SolutionRuntimeError("solution diagram specifications are invalid")
    return diagrams


def _diagram_uploads(
    context: _SolutionContext,
    target: PreparedFigure,
    analysis: GeometryAnalysis,
    content: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Reuse, upload, or preview every explicit strategy diagram."""

    solution = next(
        (
            section
            for section in content.get("sections", [])
            if isinstance(section, dict) and section.get("key") == "solution"
        ),
        None,
    )
    existing = str(solution.get("html") or "") if solution else ""
    if (
        context.profile.existing_solution_policy == "preserve"
        and existing.strip()
        and not re.search(r'<section\b[^>]*\bdata-content-kind\s*=', existing, re.I)
    ):
        return ()

    results: list[dict[str, Any]] = []
    for diagram in _diagram_specs(context, target, analysis):
        digest = hashlib.sha256(diagram.svg_bytes).hexdigest()
        uploaded = _existing_solution_asset(
            context,
            content,
            diagram.asset_key,
            digest,
        )
        attached = uploaded is not None
        if context.apply and uploaded is None:
            uploaded = context.gateway.upload_solution_asset(
                source_problem_id=target.source_problem_id,
                svg_bytes=diagram.svg_bytes,
                sha256=digest,
            )
            current = [
                asset
                for asset in content.get("assets", [])
                if isinstance(asset, dict) and asset.get("asset_key") == diagram.asset_key
            ]
            if len(current) == 1:
                context.gateway.replace_problem_asset_target(
                    problem_id=target.problem_id,
                    transformation_target_id=f"asset:{diagram.asset_key}",
                    replacement_asset_id=str(uploaded["source_asset_id"]),
                    alt_text=diagram.alt_text,
                )
                attached = True
        if uploaded is None:
            uploaded = {
                "source_asset_id": f"preview-{digest[:16]}",
                "url": f"/assets/preview-{digest[:16]}",
                "sha256": digest,
            }
        results.append(
            {
                **uploaded,
                "asset_key": diagram.asset_key,
                "solution_variant_index": diagram.solution_variant_index,
                "alt_text": diagram.alt_text,
                "already_attached": attached,
            }
        )
    return tuple(results)


def _existing_solution_asset(
    context: _SolutionContext,
    content: dict[str, Any],
    asset_key: str,
    expected_sha256: str,
) -> dict[str, str] | None:
    """Resolve a reusable solution asset through normalized or asset readback."""

    resolved = existing_solution_asset(content, asset_key, expected_sha256)
    if resolved is not None:
        return resolved
    matches = [
        asset
        for asset in content.get("assets", [])
        if isinstance(asset, dict)
        and asset.get("asset_key") == asset_key
    ]
    if len(matches) != 1:
        return None
    asset_id = str(matches[0].get("asset_id") or "")
    if not asset_id:
        return None
    metadata = context.gateway.get_asset_metadata(asset_id)
    content_type = str(metadata.get("content_type") or "").split(";", 1)[0].lower()
    if (
        content_type != "image/svg+xml"
        or str(metadata.get("sha256") or "").lower() != expected_sha256
    ):
        return None
    return {
        "source_asset_id": asset_id,
        "url": str(metadata.get("url") or matches[0].get("url") or f"/assets/{asset_id}"),
        "sha256": expected_sha256,
    }


def _report_pair(
    context: _SolutionContext,
    target: PreparedFigure,
    progress: TargetProgress,
    solution_action: str,
    answer_action: str,
    *,
    severity: str = "success",
) -> None:
    """Emit matching solution and answer progress for one frozen position."""

    context.reporter.task(
        context.profile.theme_title,
        context.profile.group_key,
        target.source_problem_id,
        progress,
        solution_action,
        severity=severity,
        stage="solution",
    )
    context.reporter.task(
        context.profile.theme_title,
        context.profile.group_key,
        target.source_problem_id,
        progress,
        answer_action,
        severity=severity,
        stage="answer",
    )


def _already_complete_result(
    context: _SolutionContext,
    target: PreparedFigure,
    progress: TargetProgress,
    plan: SolutionPlan,
) -> ProblemStageResult:
    """Verify optional asset identity and report one exact existing plan."""

    for target_id, source_asset_id in plan.asset_target_ids:
        asset_context = context.gateway.get_problem_asset_target_context(
            target.problem_id,
            target_id,
        )
        if str(asset_context.get("current_asset_id") or "") != source_asset_id:
            raise SolutionRuntimeError(
                "existing solution asset target points to another asset"
            )
    _report_pair(
        context,
        target,
        progress,
        "SOLUTION ALREADY COMPLETE",
        "ANSWER VERIFIED",
    )
    return ProblemStageResult(
        problem_id=target.problem_id,
        source_problem_id=target.source_problem_id,
        stage="solution_answer",
        status="already_complete",
        message=f"{plan.answer_audit}; no_write_required",
    )


def _planned_result(
    context: _SolutionContext,
    target: PreparedFigure,
    progress: TargetProgress,
    plan: SolutionPlan,
) -> ProblemStageResult:
    """Report one read-only solution and answer plan."""

    _report_pair(
        context,
        target,
        progress,
        "SOLUTION PLANNED",
        "ANSWER PLANNED",
        severity="info",
    )
    return ProblemStageResult(
        problem_id=target.problem_id,
        source_problem_id=target.source_problem_id,
        stage="solution_answer",
        status="planned",
        message=plan.answer_audit,
        transformations=tuple(plan.transformations),
    )


def _apply_and_verify(
    context: _SolutionContext,
    target: PreparedFigure,
    plan: SolutionPlan,
) -> None:
    """Apply the standard one-batch plan used by established groups."""

    context.gateway.apply_problem_transformations(
        target.problem_id,
        plan.transformations,
    )
    verify_solution_plan(context.gateway, target.problem_id, plan)


def _applied_result(
    context: _SolutionContext,
    target: PreparedFigure,
    progress: TargetProgress,
    plan: SolutionPlan,
) -> ProblemStageResult:
    """Apply, verify, and report one deterministic transformation batch."""

    try:
        _apply_and_verify(context, target, plan)
    except AnswerVerificationError:
        context.reporter.task(
            context.profile.theme_title,
            context.profile.group_key,
            target.source_problem_id,
            progress,
            "SOLUTION WRITTEN",
            stage="solution",
        )
        raise
    _report_pair(
        context,
        target,
        progress,
        "SOLUTION WRITTEN",
        "ANSWER VERIFIED",
    )
    return ProblemStageResult(
        problem_id=target.problem_id,
        source_problem_id=target.source_problem_id,
        stage="solution_answer",
        status="applied",
        message=f"{plan.answer_audit}; verified_after_write",
    )


def _run_target(
    context: _SolutionContext,
    target: PreparedFigure,
    progress: TargetProgress,
) -> ProblemStageResult:
    """Build and execute one target's deterministic solution plan."""

    analysis = context.strategy.analyze(target, context.profile)
    if analysis.area != analysis.area_by_coordinates:
        raise SolutionRuntimeError("strategy and coordinate areas disagree")
    content = normalized_content(
        context.gateway.get_problem_context(target.problem_id)
    )
    uploaded = _diagram_uploads(context, target, analysis, content)
    plan = build_solution_plan(
        content,
        target,
        analysis,
        context.profile,
        context.strategy,
        uploaded,
    )
    if context.apply and content_matches_plan(content, plan):
        return _already_complete_result(context, target, progress, plan)
    if not context.apply:
        return _planned_result(context, target, progress, plan)
    return _applied_result(context, target, progress, plan)


def _failed_result(
    context: _SolutionContext,
    target: PreparedFigure,
    progress: TargetProgress,
    exc: Exception,
) -> ProblemStageResult:
    """Report one isolated solution or answer failure."""

    answer_failed = isinstance(exc, AnswerVerificationError)
    stage = "answer" if answer_failed else "solution"
    context.reporter.task(
        context.profile.theme_title,
        context.profile.group_key,
        target.source_problem_id,
        progress,
        "ANSWER FAILED" if answer_failed else "SOLUTION FAILED",
        severity="error",
        stage=stage,
        details={"exception_type": type(exc).__name__, "exception": str(exc)},
    )
    return ProblemStageResult(
        problem_id=target.problem_id,
        source_problem_id=target.source_problem_id,
        stage=stage,
        status="failed",
        message=" ".join(str(exc).split())[:2000],
    )


def _run_isolated_target(
    context: _SolutionContext,
    indexed_target: tuple[int, PreparedGridPolygon],
) -> ProblemStageResult:
    """Run one frozen target and convert every failure into a stage result."""

    index, target = indexed_target
    progress = TargetProgress(index=index, total=context.total)
    try:
        return _run_target(context, target, progress)
    except Exception as exc:  # noqa: BLE001 - target isolation is intentional.
        return _failed_result(context, target, progress, exc)


def run_solution_stage(
    gateway: SolutionGateway,
    prepared: tuple[PreparedFigure, ...],
    profile: GroupProfile,
    strategy: SolutionStrategy,
    reporter: ProgressReporter,
    *,
    apply: bool,
    max_workers: int = 1,
) -> tuple[ProblemStageResult, ...]:
    """Process every frozen target independently and continue after failures."""

    if max_workers <= 0:
        raise ValueError("max_workers must be positive")
    if not prepared:
        return ()
    context = _SolutionContext(
        gateway=gateway,
        profile=profile,
        strategy=strategy,
        reporter=reporter,
        apply=apply,
        total=len(prepared),
    )
    indexed_targets = tuple(enumerate(prepared, start=1))
    run_target = partial(_run_isolated_target, context)
    if max_workers == 1:
        return tuple(map(run_target, indexed_targets))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return tuple(executor.map(run_target, indexed_targets))
