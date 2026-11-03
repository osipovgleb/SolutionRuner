"""Prepare altitude/bisector intersections without assuming the parent's ray order."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..isosceles.planner import RepairPlan, _section
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .height_bisector_figures import SOURCE
from .height_bisector_figures import prepare as prepare_figures
from .height_bisector_proofs import render, review_parent


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
):
    review_parent(parent_solution_html)
    if parent_condition_asset_id != SOURCE or parent_solution_assets:
        raise ContentPlanError("the reviewed height/bisector parent assets changed")
    model, changes = prepare_figures(context, generated_solution_assets)
    content = context["normalized_content"]
    plan = diagrams.repair(
        _section(content, "condition"),
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        exact_answer(model.answer),
        render(model),
        asset_changes=changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
