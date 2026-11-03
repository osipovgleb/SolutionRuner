"""Prepare reviewed internal, exterior and altitude angle families with one handler."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .angle_figures import (
    ALTITUDE,
    DIFFERENCE,
    EXTERIOR_BASE,
    EXTERIOR_GIVEN,
    EXTERIOR_VERTEX,
    LARGER,
)
from .angle_figures import prepare as prepare_figures
from .angle_proofs import render, review_parent
from .area_figures import ACUTE
from .planner import RepairPlan, _section

_PARENTS = {
    "isosceles-triangle-27760-vertex-angle-from-altitude-angle": ALTITUDE,
    "isosceles-triangle-27744-vertex-angle-from-base-angle": ACUTE,
    "isosceles-triangle-27745-base-angle-from-vertex-angle": ACUTE,
    "isosceles-triangle-27746-exterior-angle-from-vertex-angle": EXTERIOR_BASE,
    "isosceles-triangle-27747-vertex-angle-from-exterior-base-angle": EXTERIOR_GIVEN,
    "isosceles-triangle-27748-base-angle-from-exterior-vertex-angle": EXTERIOR_VERTEX,
    "isosceles-triangle-27750-smaller-angle-from-larger-angle": LARGER,
    "isosceles-triangle-27754-smaller-angle-from-angle-difference": DIFFERENCE,
}


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
    content_rule_key,
):
    review_parent(parent_solution_html, content_rule_key)
    if (
        parent_condition_asset_id != _PARENTS[content_rule_key]
        or parent_solution_assets
    ):
        raise ContentPlanError(
            "the reviewed angle parent has one condition image and no solution images"
        )
    model, changes = prepare_figures(context, generated_solution_assets)
    model.require_rule(content_rule_key)
    content = context["normalized_content"]
    plan = diagrams.repair(
        _section(content, "condition"),
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        exact_answer(model.answer),
        render(model, content_rule_key),
        asset_changes=changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
