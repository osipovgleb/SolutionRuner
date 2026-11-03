"""Prepare canonical quantity solutions and exact answers without transport effects."""

from html import escape

from ..probability.solution_diagrams import repair
from ..triangles.isosceles.planner import RepairPlan, _section
from ..triangles.right.basic_parent import _targeted
from ..word_problems.common import rewrite
from .parallelogram.rectangle_proofs import value


def repair_quantity(context, amount, html, keys=(), changes=()):
    content = context["normalized_content"]
    answer = value(amount).replace("{,}", ",")
    current_answer = _targeted(_section(content, "answer"))
    result = repair(
        _section(content, "condition"),
        current_answer,
        _targeted(_section(content, "solution")),
        answer,
        html,
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
