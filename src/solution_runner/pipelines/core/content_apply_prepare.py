"""Rebuild frozen content plans before applying any transformation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .content_context import _preserving_solution_transformations
from .content_diagrams import _generated_diagram_assets
from .content_gateway import RightTriangleGateway
from .content_readback import _validate_frozen_presentation
from .errors import ContentPlanError as RightTrianglePlanError


@dataclass(frozen=True)
class _PreparedApply:
    """Current plan and diagram state checked against a frozen record."""

    context: dict[str, Any]
    handler: Any
    condition_asset_bytes: bytes | None
    diagram_specs: Any
    generated_assets: Any
    current_plan: Any
    current_transformations: list[dict[str, Any]]
    frozen: list[dict[str, Any]]


def _prepare_frozen_apply(
    gateway: RightTriangleGateway, record: dict[str, Any], parent: Any, *, services: Any
) -> _PreparedApply:
    """Rebuild and validate the plan before any mutation is attempted."""

    problem_id = str(record.get("problem_id") or "")
    source_problem_id = str(record.get("source_problem_id") or "")
    parent_asset_id = parent.asset_id
    content_rule_key = parent.rule_key
    parent_solution_assets = parent.solution_assets
    parent_solution_html = parent.solution_html
    context = gateway.get_problem_context(problem_id)
    context = services._ensure_required_assets(
        gateway, problem_id, context, content_rule_key
    )
    if (
        services._registered_handler(content_rule_key).strict_frozen_input
        and context.get("problem_id") != problem_id
    ):
        raise RightTrianglePlanError("current problem identity drifted")
    current_asset_content_type = services._current_condition_asset_content_type(
        gateway, context, content_rule_key
    )
    condition_asset_bytes = services._condition_asset_bytes(
        gateway, problem_id, source_problem_id, content_rule_key
    )
    handler = services._registered_handler(content_rule_key)
    diagram_specs = (
        handler.diagram_specs(context, condition_asset_bytes=condition_asset_bytes)
        if handler.diagram_builder_uses_condition_bytes
        else handler.diagram_specs(context)
    )
    if list(diagram_specs) != record.get("generated_diagrams", []):
        raise RightTrianglePlanError("generated diagram drifted after prepare")
    generated_assets = _generated_diagram_assets(
        gateway,
        context,
        diagram_specs,
        source_problem_id,
        **(
            {"condition_asset_bytes": condition_asset_bytes}
            if handler.diagram_builder_uses_condition_bytes
            else {}
        ),
    )
    current_plan = services._build_content_plan(
        context,
        parent_asset_id=parent_asset_id,
        content_rule_key=content_rule_key,
        parent_solution_assets=parent_solution_assets,
        parent_solution_html=parent_solution_html,
        current_asset_content_type=current_asset_content_type,
        condition_asset_bytes=condition_asset_bytes,
        generated_solution_assets=generated_assets,
    )
    expected_answer = str(record.get("expected_answer") or "")
    frozen = record.get("transformations")
    if not isinstance(frozen, list) or (
        not expected_answer
        and not services._registered_handler(content_rule_key).presentation_only
    ):
        raise RightTrianglePlanError("prepared record is incomplete")
    if current_plan.answer != expected_answer:
        raise RightTrianglePlanError(
            "condition or computed answer drifted after prepare"
        )
    current_transformations = list(current_plan.transformations)
    if record.get("preserve_existing_solution") is True:
        current_transformations = list(
            _preserving_solution_transformations(
                context, tuple(current_transformations)
            )
        )
    if services._registered_handler(content_rule_key).presentation_only:
        _validate_frozen_presentation(frozen)
    return _PreparedApply(
        context,
        handler,
        condition_asset_bytes,
        diagram_specs,
        generated_assets,
        current_plan,
        current_transformations,
        frozen,
    )
