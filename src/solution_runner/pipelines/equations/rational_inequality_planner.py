"""One pure planner with explicit reviewed parent methods and chart requirements."""

import hashlib

from ..probability.common import UnsupportedCondition
from ..word_problems.common import RepairPlan, rewrite
from .rational_inequality import set_latex
from .rational_inequality_algebraic_methods import presentation
from .rational_inequality_figures import SOURCES, image, read
from .rational_inequality_proof import render


def build_context_repair_plan(
    context, *, method, parent_solution_html="", generated_solution_assets=()
):
    parent = SOURCES["parents"].get(method)
    if (
        parent is None
        or hashlib.sha256(parent_solution_html.encode()).hexdigest() != parent["sha256"]
    ):
        raise UnsupportedCondition("the complete reviewed parent solution is required")
    (_, condition, answer_section, solution), a = read(context)
    a = presentation(a, method)
    markup, keys, asset_changes = image(
        context, a, generated_solution_assets, required=parent["required_chart"]
    )
    html = render(a, method, markup)
    answer = set_latex(a.solution)
    answer_html = '<p><span data-inline-latex="' + answer + '"></span></p>'
    changes = list(asset_changes)
    if answer_section is None or answer_section.get("html") != answer_html:
        changes.append(rewrite(answer_section, "answer", "Ответ", answer_html))
    if (
        solution is None
        or solution.get("html") != html
        or tuple(solution.get("asset_keys") or ()) != keys
    ):
        change = rewrite(solution, "solution", "Решение", html)
        change["value"]["asset_keys"] = list(keys)
        changes.append(change)
    return RepairPlan(answer, condition["html"], html, tuple(changes))
