"""Replan content and verify authoritative post-write readback."""

from __future__ import annotations

from typing import Any

from .content_context import _preserving_solution_transformations
from .content_diagrams import _generated_diagram_assets
from .content_gateway import RightTriangleGateway
from .content_readback import _check_readback_sections
from .errors import ContentPlanError as RightTrianglePlanError


def _verify_content_readback(
    gateway: RightTriangleGateway,
    record: dict[str, Any],
    context: dict[str, Any],
    frozen: list[dict[str, Any]],
    parent: Any,
    *,
    services: Any,
) -> None:
    """Replan from authoritative readback and verify all touched sections."""

    problem_id = str(record.get("problem_id") or "")
    source_problem_id = str(record.get("source_problem_id") or "")
    expected_answer = str(record.get("expected_answer") or "")
    parent_asset_id = parent.asset_id
    content_rule_key = parent.rule_key
    parent_solution_assets = parent.solution_assets
    parent_solution_html = parent.solution_html
    refreshed = gateway.get_problem_context(problem_id)
    handler = services.registered_handler(content_rule_key)
    refreshed_bytes = (
        services.condition_asset_bytes(
            gateway, problem_id, source_problem_id, content_rule_key
        )
        if handler.diagram_builder_uses_condition_bytes
        else None
    )
    refreshed_specs = (
        handler.diagram_specs(refreshed, condition_asset_bytes=refreshed_bytes)
        if handler.diagram_builder_uses_condition_bytes
        else handler.diagram_specs(refreshed)
    )
    refreshed_assets = _generated_diagram_assets(
        gateway,
        refreshed,
        refreshed_specs,
        source_problem_id,
        **(
            {"condition_asset_bytes": refreshed_bytes}
            if handler.diagram_builder_uses_condition_bytes
            else {}
        ),
    )
    verified = services.build_content_plan(
        refreshed,
        parent_asset_id=parent_asset_id,
        content_rule_key=content_rule_key,
        parent_solution_assets=parent_solution_assets,
        parent_solution_html=parent_solution_html,
        generated_solution_assets=refreshed_assets,
        **(
            {"condition_asset_bytes": refreshed_bytes}
            if handler.diagram_builder_uses_condition_bytes
            else {}
        ),
    )
    verified_transformations = verified.transformations
    if record.get("preserve_existing_solution") is True:
        verified_transformations = _preserving_solution_transformations(
            refreshed, tuple(verified_transformations)
        )
    if verified_transformations or verified.answer != expected_answer:
        raise RightTrianglePlanError("content failed authoritative readback")
    _check_readback_sections(context, refreshed, frozen)
