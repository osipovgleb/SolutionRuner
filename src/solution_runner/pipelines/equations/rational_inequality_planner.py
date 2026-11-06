"""One pure planner with explicit reviewed parent methods and chart requirements."""

import hashlib

from ..probability.common import UnsupportedCondition
from .inequality_plan import repair
from .rational_inequality import set_latex
from .rational_inequality_algebraic_methods import presentation
from .rational_inequality_figures import SOURCES, image, read
from .rational_inequality_proof import render
from .rational_inequality_substitution_figures import chart
from .rational_inequality_substitution_proof import render as render_substitution
from .rational_inequality_substitutions import METHODS as SUBSTITUTIONS
from .rational_inequality_substitutions import model


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
    if method in SUBSTITUTIONS:
        substitution = model(a, method)
        markup, keys, asset_changes = chart(
            context, substitution, generated_solution_assets
        )
        html = render_substitution(substitution, method, markup)
    else:
        a = presentation(a, method)
        markup, keys, asset_changes = image(
            context, a, generated_solution_assets, required=parent["required_chart"]
        )
        html = render(a, method, markup)
    answer = set_latex(a.solution)
    return repair(
        condition,
        answer_section,
        solution,
        answer,
        html,
        keys=keys,
        asset_changes=asset_changes,
    )
