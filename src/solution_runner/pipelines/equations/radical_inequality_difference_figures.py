"""Reuse two-row or three-row source charts after checking every plotted row."""

import json
from pathlib import Path

from ..probability import solution_diagrams
from .radical_inequality_difference import analyze
from .radical_inequality_difference_svg import render
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .rational_inequality_figures import read_formula, signature

SOURCES = json.loads(
    (Path(__file__).parent / "assets/radical-inequalities/difference.json").read_text()
)
KEY = "radical_difference_intersection"
ALT = "Рациональное неравенство, область определения корней и их пересечение"


def compatible(entry, a):
    return (
        entry.get("stage") == signature(a.stage)
        and entry.get("other_stage") == signature(a.other_stage)
        and (
            entry.get("rows") == 2
            or (
                entry.get("rows") == 3
                and entry.get("square_stage") == signature(a.square_stage)
            )
        )
    )


def selection(context, a):
    return select_chart(
        context,
        a,
        key=KEY,
        figures=SOURCES["figures"],
        compatible_fn=compatible,
        renderer=render,
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


def diagram_specs(context):
    a = analyze(read_formula(context)[1])
    _, svg = selection(context, a)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def chart(context, a, generated):
    return prepare_chart(context, a, generated, key=KEY, alt=ALT, selector=selection)
