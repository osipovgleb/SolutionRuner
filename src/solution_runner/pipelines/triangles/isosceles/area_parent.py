"""Prepare the five area and inverse-side families with one reviewed method."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .area_figures import ACUTE, OBTUSE
from .area_figures import prepare as prepare_figures
from .area_proofs import render, review_parent
from .planner import RepairPlan, _section

_PARENTS = {
    "isosceles-triangle-27589-area-from-side-and-30-degree-vertex-angle": ACUTE,
    "isosceles-triangle-27590-area-from-side-and-150-degree-vertex-angle": OBTUSE,
    "isosceles-triangle-27619-area-from-side-and-base": ACUTE,
    "isosceles-triangle-27620-side-from-area-and-30-degree-vertex-angle": ACUTE,
    "isosceles-triangle-27621-side-from-area-and-150-degree-vertex-angle": OBTUSE,
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
            "the reviewed area parent has one condition image and no solution images"
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
