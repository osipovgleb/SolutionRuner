"""An edge ratio must state its starting vertex, independently of saved answers."""

from dataclasses import replace
from html import escape

import sympy as sp

from ..probability.solution_diagrams import repair
from ..triangles.isosceles.planner import _section
from ..triangles.right.basic_parent import _targeted
from ..word_problems.common import rewrite


def prepare(context, model, html, keys, changes):
    numerator, denominator = model.answer.as_numer_denom()
    answer = (
        sp.latex(numerator) + ":" + sp.latex(denominator) + r"\text{, считая от }A_1"
    )
    content = context["normalized_content"]
    current = _targeted(_section(content, "answer"))
    plan = repair(
        _section(content, "condition"),
        current,
        _targeted(_section(content, "solution")),
        answer,
        html,
        keys,
        changes,
    )
    markup = (
        '<p><span data-inline-latex="' + escape(answer, quote=True) + '"></span></p>'
    )
    transformations = [
        t
        for t in plan.transformations
        if not t["transformation_target_id"].startswith("section:answer")
    ]
    if current is None or current.get("html") != markup:
        change = rewrite(current, "answer", "Ответ", markup)
        change["value"]["asset_keys"] = []
        transformations.append(change)
    return replace(plan, transformations=tuple(transformations))
