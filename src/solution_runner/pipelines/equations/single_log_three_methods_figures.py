"""Keep the exact child cubic chart separate from the original domain restrictions."""

import json
from pathlib import Path

from ..core.condition_transcriptions import transcribe_condition
from ..probability.common import UnsupportedCondition
from .logarithm_single_rationalization import analyze
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .rational_inequality_figures import read_formula, signature

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/single-log-three-methods.json"
    ).read_text()
)
KEY = "single_log_three_methods_product"
ALT = "Знаки рационализированного произведения до учёта исходной области определения"


def canonical(context):
    (_, condition, _, _), _ = read_formula(context)
    return transcribe_condition(
        context, condition, SOURCES["condition_transcriptions"], validate=read_formula
    )


def compatible(entry, a):
    return (
        entry.get("role") == "rationalized_product_before_original_domain"
        and entry.get("stage") == signature(a.product)
        and entry.get("closed")
        == [bool(a.product.solution.contains(p)) for p in a.product.points]
        and entry.get("stage_solution") == str(a.product.solution)
    )


def required_assets(context):
    if context["normalized_content"].get("assets"):
        return ()
    ctx, _ = canonical(context)
    a = analyze(read_formula(ctx)[1])
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid, entry in SOURCES["figures"].items()
        if compatible(entry, a)
    )


def unreviewed_chart(a):
    raise UnsupportedCondition("the exact reviewed child stage chart is required")


def selection(context, a):
    if not context["normalized_content"].get("assets"):
        return None, None
    return select_chart(
        context,
        a,
        key=KEY,
        figures=SOURCES["figures"],
        compatible_fn=compatible,
        renderer=unreviewed_chart,
    )


def chart(context, a):
    if not context["normalized_content"].get("assets"):
        return "", (), ()
    return prepare_chart(context, a, (), key=KEY, alt=ALT, selector=selection)
