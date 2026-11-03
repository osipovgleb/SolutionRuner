"""Prepare the reviewed midpoint-area methods without network side effects."""

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import repair
from ...triangles.isosceles.planner import RepairPlan, _section
from ...triangles.right.altitude_parent import exact_answer
from ...triangles.right.basic_parent import _targeted
from .midpoint_figures import prepare as prepare_figures
from .midpoint_model import HEIGHT
from .midpoint_proofs import render
from .midpoint_sources import review_parent


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
    content_rule_key,
):
    review_parent(
        content_rule_key,
        parent_condition_asset_id,
        parent_solution_html,
        parent_solution_assets,
    )
    model, height_only, changes, pictures, keys = prepare_figures(
        context, generated_solution_assets
    )
    model.require_rule(content_rule_key)
    if height_only != (content_rule_key == HEIGHT):
        raise ContentPlanError("the midpoint figures differ from the parent methods")
    content = context["normalized_content"]
    plan = repair(
        _section(content, "condition"),
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        exact_answer(model.answer),
        render(model, content_rule_key, pictures),
        keys,
        changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
