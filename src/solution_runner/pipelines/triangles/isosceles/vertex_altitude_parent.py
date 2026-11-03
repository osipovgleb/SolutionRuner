"""Prepare the four side-altitude/vertex-angle families with all parent methods."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .planner import RepairPlan, _section
from .vertex_altitude_figures import ACUTE, OBTUSE
from .vertex_altitude_figures import prepare as prepare_figures
from .vertex_altitude_proofs import render, review_parent

_PARENTS = {
    "isosceles-triangle-27795-altitude-from-side-vertex-angle": ACUTE,
    "isosceles-triangle-27796-angle-from-side-altitude": ACUTE,
    "isosceles-triangle-27797-side-from-altitude-vertex-angle": ACUTE,
    "isosceles-triangle-27798-obtuse-altitude-from-side-angle": OBTUSE,
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
            "the reviewed vertex-altitude parent has one condition image and no solution images"
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
