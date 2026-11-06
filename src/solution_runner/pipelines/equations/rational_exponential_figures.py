"""Reuse the reviewed t-axis diagrams with exact domains and zero multiplicities."""

import json
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .rational_exponential_substitution import analyze
from .rational_inequality_figures import read_formula, reviewed_asset, signature
from .rational_inequality_parser import X, polynomial

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/exponential-inequalities/rational-substitutions.json"
    ).read_text()
)
ALT = "Метод интервалов для положительной показательной замены t"
KEY = "rational_exponential_sign_chart"


def multiplicity(value, root):
    p = polynomial(value)
    for order in range(p.degree() + 1):
        if sp.simplify(p.diff((X, order)).eval(root)) != 0:
            return order
    raise UnsupportedCondition("a chart multiplicity must be finite")


def row_signature(a):
    n, d = sp.fraction(a.stage.expression)
    return {
        **signature(a.stage),
        "variable": "t",
        "positive_solution": str(a.positive_solution),
        "holes": list(map(str, a.stage.holes)),
        "extra_poles": list(map(str, a.extra_poles)),
        "multiplicities": {
            "zeros": {str(p): multiplicity(n, p) for p in a.stage.zeros},
            "poles": {str(p): multiplicity(d, p) for p in a.stage.poles},
        },
        "display_scope": "positive_substitution_with_zero_arc"
        if any(p < 0 for p in a.stage.zeros)
        else "rational_intervals_with_double_zero_loop",
    }


def source(a):
    expected = row_signature(a)
    matches = [
        key
        for key, entry in SOURCES["figures"].items()
        if all(entry.get(k) == v for k, v in expected.items())
    ]
    if len(matches) != 1:
        raise UnsupportedCondition(
            "this t-axis chart needs one exactly compatible reviewed source"
        )
    return matches[0]


def required_assets(context):
    key = source(analyze(read_formula(context)[1]))
    if any(
        a.get("asset_id") == key
        for a in context["normalized_content"].get("assets", [])
    ):
        return ()
    return ({"source_asset_id": key, "section_id": "solution:1", "alt_text": ALT},)


def chart(context, a):
    key = source(a)
    assets = context["normalized_content"].get("assets", [])
    if len(assets) != 1 or assets[0].get("asset_id") != key:
        raise UnsupportedCondition("reuse the exact t-axis figure without duplicates")
    reviewed_asset(assets[0], figures=SOURCES["figures"])
    html, asset_key, changes = solution_diagrams.image(
        context["normalized_content"], KEY, ALT, source_id=key
    )
    return html, (asset_key,), tuple(changes)
