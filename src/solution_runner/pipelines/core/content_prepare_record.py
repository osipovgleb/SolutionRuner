"""Prepare one immutable content repair without mutating source content."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .content_context import (
    _context_fingerprint,
    _preserving_solution_transformations,
    _problem_identity,
)
from .content_diagrams import _generated_diagram_assets
from .content_gateway import RightTriangleGateway


def _prepared_record(
    gateway: RightTriangleGateway,
    child: dict[str, Any],
    parent_asset_id: str | None,
    content_rule_key: str | None = None,
    parent_solution_assets: tuple[dict[str, str], ...] = (),
    parent_solution_html: str = "",
    preserve_existing_solution: bool = False,
    *,
    services: Any,
) -> dict[str, Any]:
    """Freeze one group's current plan without changing source content."""

    problem_id, source_problem_id = _problem_identity(child)
    context = None
    condition_asset_bytes = None
    handler = None
    try:
        handler = services._registered_handler(content_rule_key)
        context = gateway.get_problem_context(problem_id)
        context = services._with_required_assets(context, content_rule_key)
        current_asset_content_type = services._current_condition_asset_content_type(
            gateway, context, content_rule_key
        )
        condition_asset_bytes = services._condition_asset_bytes(
            gateway, problem_id, source_problem_id, content_rule_key
        )
        diagram_specs = (
            handler.diagram_specs(context, condition_asset_bytes=condition_asset_bytes)
            if handler.diagram_builder_uses_condition_bytes
            else handler.diagram_specs(context)
        )
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
        plan = services._build_content_plan(
            context,
            parent_asset_id=parent_asset_id,
            content_rule_key=content_rule_key,
            parent_solution_assets=parent_solution_assets,
            parent_solution_html=parent_solution_html,
            current_asset_content_type=current_asset_content_type,
            condition_asset_bytes=condition_asset_bytes,
            generated_solution_assets=generated_assets,
        )
        transformations = tuple(plan.transformations)
        if preserve_existing_solution:
            transformations = _preserving_solution_transformations(
                context, transformations
            )
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "prepared",
            "input_fingerprint": _context_fingerprint(context),
            "expected_answer": plan.answer,
            "generated_diagrams": list(diagram_specs),
            "transformations": [deepcopy(item) for item in transformations],
            **(
                {"preserve_existing_solution": True}
                if preserve_existing_solution
                else {}
            ),
            **(
                {"message": "; ".join(plan.warnings)}
                if getattr(plan, "warnings", ())
                else {}
            ),
        }
    except Exception as exc:  # noqa: BLE001 - freeze one explicit blocker per task.
        review = None
        if handler is not None and context is not None and handler.review_builder:
            try:
                review = handler.review_preview(
                    context, condition_asset_bytes=condition_asset_bytes, error=str(exc)
                )
            except Exception:  # noqa: BLE001 - diagnostics must never change the blocked status.
                review = None
        return {
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "status": "blocked",
            "message": " ".join(str(exc).split())[:500],
            "transformations": [],
            **({"review_preview": review} if review is not None else {}),
        }
