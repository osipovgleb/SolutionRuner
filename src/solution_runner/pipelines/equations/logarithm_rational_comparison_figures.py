"""Reuse exact two-row sign/domain charts for rational logarithm comparisons."""

import json
from pathlib import Path

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .logarithm_power_quotient import analyze as power_quotient
from .rational_inequality import FLIPPED
from .rational_inequality_algebraic_methods import original_orientation
from .rational_inequality_figures import read_formula, reviewed_asset, signature
from .rational_substitution_preimages import comparison

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/rational-comparison.json"
    ).read_text()
)
ALT = "Метод интервалов и ограничения положительности аргументов логарифмов"


def row_signature(a, method):
    stage = (
        comparison(-a.stage.original, FLIPPED[a.operator])
        if method == "quadratic_quotient"
        else a.stage
    )
    return {
        "method": method,
        "stage": signature(original_orientation(stage)),
        "domain": str(a.domain),
        "intersection": str(a.solution),
        "holes": list(map(str, a.argument_holes)),
    }


def compatible(entry, a, method):
    return all(
        entry.get(key) == value for key, value in row_signature(a, method).items()
    )


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = power_quotient(read_formula(context)[1])
    matches = [
        uid
        for uid, entry in SOURCES["figures"].items()
        if compatible(entry, a, "power_quotient")
    ]
    return (
        ({"source_asset_id": matches[0], "section_id": "solution:1", "alt_text": ALT},)
        if matches
        else ()
    )


def chart(context, a, method):
    content, condition, *_ = read_formula(context)[0]
    assets = content.get("assets", [])
    if condition.get("asset_keys") or len(assets) > 1:
        raise UnsupportedCondition("only one reviewed solution chart is supported")
    if not assets:
        if method == "power_quotient":
            raise UnsupportedCondition(
                "the parent's exact cubic intersection chart is required"
            )
        return "", (), ()
    asset = assets[0]
    entry = reviewed_asset(asset, figures=SOURCES["figures"])
    if asset["asset_id"] in condition["html"] or not compatible(entry, a, method):
        raise UnsupportedCondition(
            "the plotted stage, domain and intersection must all match"
        )
    html, key, changes = solution_diagrams.image(
        content, "logarithm_rational_intersection", ALT, source_id=asset["asset_id"]
    )
    return html, (key,), tuple(changes)
