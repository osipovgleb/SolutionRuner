"""Reuse complete reviewed charts, including double poles and isolated zeros."""

import json
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .exponential_squared_denominator import analyze
from .exponential_squared_denominator_svg import render
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


def matching(a):
    return [key for key, entry in SOURCES["figures"].items() if compatible(entry, a)]


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = analyze(read_formula(context)[1])
    matches = matching(a)
    if not matches:
        return ()
    # Every match certifies the same full chart; reuse an existing asset.
    return (
        {"source_asset_id": matches[0], "section_id": "solution:1", "alt_text": ALT},
    )


def selection(context, a):
    assets = context["normalized_content"].get("assets", [])
    original = [asset for asset in assets if asset.get("asset_key") != KEY]
    generated = [asset for asset in assets if asset.get("asset_key") == KEY]
    if len(original) > 1 or len(generated) > 1:
        raise UnsupportedCondition(
            "one source chart and one prepared chart are supported"
        )
    if original:
        entry = reviewed_asset(original[0], figures=SOURCES["figures"])
        if not compatible(entry, a) or generated:
            raise UnsupportedCondition(
                "reuse the complete compatible source chart without duplicates"
            )
        return original[0]["asset_id"], None
    if not generated:
        matches = matching(a)
        if matches:
            return matches[0], None
    return None, render(a.stage)


def diagram_specs(context):
    _, svg = selection(context, analyze(read_formula(context)[1]))
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def chart(context, a, generated=()):
    source_id, svg = selection(context, a)
    if source_id is not None and generated:
        raise UnsupportedCondition("an exact source chart needs no generated duplicate")
    html, key, changes = solution_diagrams.image(
        context["normalized_content"],
        KEY,
        ALT,
        source_id=source_id,
        svg=svg,
        generated=generated,
    )
    return html, (key,), tuple(changes)
