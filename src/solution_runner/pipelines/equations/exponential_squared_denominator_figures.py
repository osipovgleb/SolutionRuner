"""Reuse complete reviewed charts, including double poles and isolated zeros."""

import json
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .exponential_squared_denominator import analyze
from .rational_exponential_figures import multiplicity
from .rational_inequality_figures import read_formula, reviewed_asset, signature

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/exponential-inequalities/squared-denominator.json"
    ).read_text()
)
KEY = "exponential_squared_denominator_chart"
ALT = "Метод интервалов: двойные полюсы знаменателя и нули числителя"


def row_signature(a):
    n, d = sp.fraction(a.stage.expression)
    return {
        **signature(a.stage),
        "variable": "x",
        "solution": str(a.solution),
        "holes": list(map(str, a.stage.holes)),
        "multiplicities": {
            "zeros": {str(z): multiplicity(n, z) for z in a.stage.zeros},
            "poles": {str(z): multiplicity(d, z) for z in a.stage.poles},
        },
    }


def compatible(entry, a):
    return all(entry.get(k) == v for k, v in row_signature(a).items())


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = analyze(read_formula(context)[1])
    matches = [key for key, entry in SOURCES["figures"].items() if compatible(entry, a)]
    if not matches:
        return ()
    # Every match certifies the same full chart; reuse an existing asset.
    return (
        {"source_asset_id": matches[0], "section_id": "solution:1", "alt_text": ALT},
    )


def chart(context, a):
    assets = context["normalized_content"].get("assets", [])
    if len(assets) != 1:
        raise UnsupportedCondition(
            "one exact reviewed squared-denominator chart is required"
        )
    entry = reviewed_asset(assets[0], figures=SOURCES["figures"])
    if not compatible(entry, a):
        raise UnsupportedCondition(
            "the chart zeros, poles, signs and multiplicities must match"
        )
    html, key, changes = solution_diagrams.image(
        context["normalized_content"], KEY, ALT, source_id=assets[0]["asset_id"]
    )
    return html, (key,), tuple(changes)
