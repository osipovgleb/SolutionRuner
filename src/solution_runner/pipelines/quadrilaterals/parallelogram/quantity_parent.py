"""Prepare the reviewed height and rhombus methods without transport side effects."""

from html import escape

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import repair
from ...triangles.isosceles.planner import RepairPlan, _section
from ...triangles.right.basic_parent import _targeted
from ...word_problems.common import rewrite
from .quantity_figures import prepare as prepare_figures
from .quantity_model import RULES
from .quantity_proofs import render
from .quantity_sources import review_parent
from .rectangle_proofs import value


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
    model, changes, pictures, keys = prepare_figures(context, generated_solution_assets)
    if RULES[content_rule_key] != model.mode:
        raise ContentPlanError(
            "the complete quantity question differs from its parent method"
        )
    content = context["normalized_content"]
    answer = value(model.answer).replace("{,}", ",")
    current_answer = _targeted(_section(content, "answer"))
    result = repair(
        _section(content, "condition"),
        current_answer,
        _targeted(_section(content, "solution")),
        answer,
        render(model, pictures),
        keys,
        changes,
    )
    transformations = list(result.transformations)
    if "\\" in answer:
        transformations = [
            t
            for t in transformations
            if not t["transformation_target_id"].startswith("section:answer")
        ]
        markup = (
            '<p><span data-inline-latex="'
            + escape(answer, quote=True)
            + '"></span></p>'
        )
        if current_answer is None or current_answer.get("html") != markup:
            change = rewrite(current_answer, "answer", "Ответ", markup)
            change["value"]["asset_keys"] = []
            transformations.append(change)
    return RepairPlan(answer, tuple(transformations))
