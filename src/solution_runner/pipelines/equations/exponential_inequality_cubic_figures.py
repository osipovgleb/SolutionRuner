"""Reuse certified cubic-zero/square-pole charts or prepare the same local style."""

import json
from pathlib import Path

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .exponential_inequality_factorizations import cube_over_square
from .rational_inequality_figures import read_formula, reviewed_asset, signature
from .rational_inequality_hatched_svg import cubic_points, render_cubic

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/exponential-inequalities/cubic-square.json"
    ).read_text()
)
KEY = "exponential_cubic_sign_chart"
ALT = "Метод интервалов: нуль кратности 3 и исключённая точка кратности 2"


def row_signature(a):
    zero, pole = cubic_points(a)
    return {
        **signature(a),
        "variable": "x",
        "multiplicities": {"zeros": {str(zero): 3}, "poles": {str(pole): 2}},
    }


def compatible(entry, a):
    return all(entry.get(key) == value for key, value in row_signature(a).items())


def required_assets(context):
    if any(
        a.get("asset_key") != KEY
        for a in context["normalized_content"].get("assets", [])
    ):
        return ()
    a = cube_over_square(read_formula(context)[1]).stage
    matches = [key for key, entry in SOURCES["figures"].items() if compatible(entry, a)]
    if len(matches) > 1:
        raise UnsupportedCondition("the compatible cubic source chart must be unique")
    if not matches:
        return ()
    return (
        {"source_asset_id": matches[0], "section_id": "solution:1", "alt_text": ALT},
    )


def selection(context, a):
    assets = context["normalized_content"].get("assets", [])
    original = [asset for asset in assets if asset.get("asset_key") != KEY]
    generated = [asset for asset in assets if asset.get("asset_key") == KEY]
    if len(original) > 1 or len(generated) > 1:
        raise UnsupportedCondition(
            "at most one source chart and one prepared cubic chart are reviewed"
        )
    if original:
        asset = original[0]
        entry = reviewed_asset(asset, figures=SOURCES["figures"])
        if compatible(entry, a):
            if generated:
                raise UnsupportedCondition(
                    "an exactly compatible cubic chart needs no duplicate"
                )
            return asset["asset_id"], None
    return None, render_cubic(a)


def diagram_specs(context):
    a = cube_over_square(read_formula(context)[1])
    _, svg = selection(context, a.stage)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def chart(context, a, generated):
    source_id, svg = selection(context, a.stage)
    if source_id is not None and generated:
        raise UnsupportedCondition("the exact compatible cubic chart must be reused")
    html, key, changes = solution_diagrams.image(
        context["normalized_content"],
        KEY,
        ALT,
        source_id=source_id,
        svg=svg,
        generated=generated,
    )
    return html, (key,), tuple(changes)
