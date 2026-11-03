"""Prepare the shared exterior-angle and bisector family in the parents' methods."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..isosceles.planner import RepairPlan, _section
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .simple_angle_figures import SOURCES
from .simple_angle_figures import prepare as prepare_figures
from .simple_angle_model import RULES
from .simple_angle_proofs import render, review_parent


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
        parent_condition_asset_id != SOURCES[RULES[content_rule_key]]
        or parent_solution_assets
    ):
        raise ContentPlanError("the reviewed simple-angle parent images changed")
    model, changes = prepare_figures(context, generated_solution_assets)
    model.require_rule(content_rule_key)
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
