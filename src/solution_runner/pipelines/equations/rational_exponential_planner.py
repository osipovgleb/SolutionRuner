"""Prepare a certified common-denominator substitution proof without source writes."""

import hashlib

from ..probability.common import UnsupportedCondition
from .inequality_plan import repair
from .rational_exponential_figures import SOURCES, chart
from .rational_exponential_proof import render
from .rational_exponential_substitution import analyze
from .rational_inequality_figures import read_formula


def build_context_repair_plan(
    context, *, parent_solution_html="", requires_chart=False
):
    frame = SOURCES["parents"].get(
        hashlib.sha256(parent_solution_html.encode()).hexdigest()
    )
    if frame is None or frame["requires_chart"] != requires_chart:
        raise UnsupportedCondition(
            "the complete reviewed parent and its diagram frame are required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    if requires_chart:
        image, keys, changes = chart(context, a)
    else:
        if content.get("assets"):
            raise UnsupportedCondition(
                "this reviewed substitution parent has no diagrams"
            )
        image, keys, changes = "", (), ()
    return repair(
        condition,
        answer,
        solution,
        a.answer,
        render(a, frame["variable"], image),
        keys=keys,
        asset_changes=changes,
    )
