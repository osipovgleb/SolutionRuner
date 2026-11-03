"""Prepare equilateral height pairs and the two reviewed base/height angle methods."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .base_height_figures import SOURCE
from .base_height_figures import prepare as prepare_figures
from .base_height_proofs import render, review_parent
from .planner import RepairPlan, _section


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
    if parent_condition_asset_id != SOURCE or parent_solution_assets:
        raise ContentPlanError(
            "the reviewed base-height parent has one condition image and no solution images"
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
