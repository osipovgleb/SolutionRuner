"""Prepare a certified common-denominator substitution proof without source writes."""

import hashlib

from ..probability.common import UnsupportedCondition
from .inequality_plan import repair
from .rational_exponential_division import render as division_render
from .rational_exponential_division_figures import SOURCES as DIVISION_SOURCES
from .rational_exponential_division_figures import chart as division_chart
from .rational_exponential_figures import SOURCES, chart
from .rational_exponential_proof import render
from .rational_exponential_substitution import analyze
from .rational_inequality_figures import read_formula

PARENTS = {**SOURCES["parents"], **DIVISION_SOURCES["parents"]}


def build_context_repair_plan(
    context,
    *,
    parent_solution_html="",
    requires_chart=False,
    method="common",
    generated_solution_assets=(),
):
    frame = PARENTS.get(hashlib.sha256(parent_solution_html.encode()).hexdigest())
    if (
        frame is None
        or frame["requires_chart"] != requires_chart
        or frame.get("method", "common") != method
    ):
        raise UnsupportedCondition(
            "the complete reviewed parent and its diagram frame are required"
        )
    (content, condition, answer, solution), formula = read_formula(context)
    a = analyze(formula)
    if method != "common":
        image, keys, changes = division_chart(
            context, a, generated_solution_assets, required=requires_chart
        )
        return repair(
            condition,
            answer,
            solution,
            a.answer,
            division_render(a, frame["variable"], image, method=method),
            keys=keys,
            asset_changes=changes,
        )
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
