"""Reuse compatible child interval charts without creating a chart for the parent."""

import json
from pathlib import Path

from .exponential_log_product import analyze
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/exponential-product.json"
    ).read_text()
)
KEY = "exponential_log_product_intervals"
ALT = "Знаки произведения на исходной области определения логарифмов"


def compatible(entry, a):
    return (
        entry.get("points") == list(map(str, a.points))
        and entry.get("signs") == list(a.signs)
        and entry.get("operator") == a.operator
        and entry.get("solution") == str(a.solution)
        and entry.get("role") == "overall_product_signs_on_original_domain"
    )


def selection(context, a):
    return select_chart(
        context,
        a,
        key=KEY,
        figures=SOURCES["figures"],
        compatible_fn=compatible,
        renderer=lambda _: None,
    )


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    a = analyze(read_formula(context)[1])
    matches = [uid for uid, e in SOURCES["figures"].items() if compatible(e, a)]
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid in matches[:1]
    )


def chart(context, a):
    uid, _ = selection(context, a)
    if uid is None:
        return "", (), ()
    return prepare_chart(context, a, (), key=KEY, alt=ALT, selector=selection)
