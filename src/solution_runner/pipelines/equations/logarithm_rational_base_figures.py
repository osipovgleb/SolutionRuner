"""Reuse the parent's exact two systems or render matching child systems."""

import json
from pathlib import Path

from ..core.condition_transcriptions import transcribe_condition
from ..probability import solution_diagrams
from .logarithm_rational_base_cases import analyze
from .logarithm_rational_base_svg import render, signature
from .logarithm_square_difference_figures import charts as prepare_charts
from .logarithm_square_difference_figures import selection as select_chart
from .rational_inequality_figures import read_formula

SOURCES = json.loads(
    (
        Path(__file__).parent
        / "assets/logarithmic-inequalities/rational-base-cases.json"
    ).read_text()
)
KEYS = ("logarithm_rational_base_above", "logarithm_rational_base_below")
ALT = "Условия рассматриваемого случая основания и их пересечение"


def canonical(context):
    (_, condition, _, _), _ = read_formula(context)
    return transcribe_condition(
        context, condition, SOURCES["condition_transcriptions"], validate=read_formula
    )


def compatible(entry, a, index):
    return (
        entry.get("role") == "base_case_row_intersection"
        and entry.get("branch") == index
        and entry.get("signature") == signature(a.cases[index])
    )


def required_assets(context):
    ctx, _ = canonical(context)
    a = analyze(read_formula(ctx)[1])
    present = {
        asset.get("asset_id") for asset in ctx["normalized_content"].get("assets", ())
    }
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid, entry in SOURCES["figures"].items()
        if uid not in present and compatible(entry, a, entry["branch"])
    )


def selection(context, a, index):
    return select_chart(
        context,
        a,
        index,
        figures=SOURCES["figures"],
        keys=KEYS,
        compatible_fn=compatible,
        renderer=lambda value, branch: render(value.cases[branch]),
    )


def diagram_specs(context):
    ctx, _ = canonical(context)
    a = analyze(read_formula(ctx)[1])
    specs = []
    for index, key in enumerate(KEYS):
        _, svg = selection(ctx, a, index)
        if svg is not None:
            specs.append(solution_diagrams.spec(key, svg))
    return tuple(specs)


def charts(context, a, generated):
    return prepare_charts(
        context, a, generated, chart_keys=KEYS, selector=selection, alt=ALT
    )
