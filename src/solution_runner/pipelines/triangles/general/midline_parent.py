"""Prepare the shared midline area family with frozen figures and parent methods."""

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ..isosceles.planner import RepairPlan, _section
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .midline_figures import SECOND, SOURCES
from .midline_figures import prepare as prepare_figures
from .midline_model import RULES
from .midline_proofs import render, review_parent


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
    mode = RULES[content_rule_key]
    if parent_condition_asset_id != SOURCES[mode]:
        raise ContentPlanError("the reviewed midline parent condition image changed")
    expected = (("image_2", SECOND, "/assets/" + SECOND),) if mode == "total" else ()
    actual = tuple(
        (a.get("asset_key"), a.get("source_asset_id"), a.get("url"))
        for a in parent_solution_assets
    )
    if actual != expected:
        raise ContentPlanError("the reviewed midline parent solution images changed")
    model, changes, image, keys = prepare_figures(context, generated_solution_assets)
    model.require_rule(content_rule_key)
    content = context["normalized_content"]
    plan = diagrams.repair(
        _section(content, "condition"),
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        exact_answer(model.answer),
        render(model, image),
        keys,
        changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
