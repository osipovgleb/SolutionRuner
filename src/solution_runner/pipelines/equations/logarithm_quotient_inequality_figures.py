"""Reuse three-row charts only for the exact displayed denominator scope."""

import json
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .logarithm_product_inequality import analyze
from .rational_exponential_figures import multiplicity
from .rational_inequality_figures import read_formula, reviewed_asset, signature

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/quotient-comparison.json"
    ).read_text()
)
KEY = "logarithm_quotient_intersection"
ALT = "Пересечение условий положительности аргументов и рационального неравенства"


def stage_for(a, scope):
    if scope == "positive_factor_removed":
        return a.stage
    if scope == "full_denominator" and a.full_stage is not None:
        return a.full_stage
    raise UnsupportedCondition(
        "the reviewed chart needs an exact full or reduced denominator scope"
    )


def row_signature(a, scope):
    stage = stage_for(a, scope)
    n, d = sp.fraction(stage.expression)
    return {
        "row1_domain": str(a.domains[0].solution),
        "row2_domain": str(a.domains[1].solution),
        "bottom_scope": scope,
        "bottom_signature": signature(stage),
        "bottom_solution": str(stage.solution),
        "multiplicities": {
            "zeros": {str(p): multiplicity(n, p) for p in stage.zeros},
            "poles": {str(p): multiplicity(d, p) for p in stage.poles},
        },
        "intersection": str(a.solution),
        "argument_holes": list(map(str, a.argument_holes)),
    }


def compatible(entry, a):
    return all(
        entry.get(k) == v for k, v in row_signature(a, entry["bottom_scope"]).items()
    )


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = analyze(read_formula(context)[1], method="quotient")
    matches = [key for key, entry in SOURCES["figures"].items() if compatible(entry, a)]
    if not matches:
        return ()
    return (
        {"source_asset_id": matches[0], "section_id": "solution:1", "alt_text": ALT},
    )


def chart(context, a):
    assets = context["normalized_content"].get("assets", [])
    if len(assets) != 1:
        raise UnsupportedCondition("one reviewed three-row logarithm chart is required")
    asset = assets[0]
    entry = reviewed_asset(asset, figures=SOURCES["figures"])
    if not compatible(entry, a):
        raise UnsupportedCondition(
            "every domain row, denominator scope and marked interval must match"
        )
    html, key, changes = solution_diagrams.image(
        context["normalized_content"], KEY, ALT, source_id=asset["asset_id"]
    )
    return html, (key,), tuple(changes), entry["bottom_scope"]
