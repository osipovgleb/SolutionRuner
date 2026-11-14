"""Match both quadratic branches before reusing exact native union charts."""

import json
from pathlib import Path

from ..probability import solution_diagrams
from .absolute_inequality import analyze
from .absolute_quadratic_svg import render
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .rational_inequality_figures import read_formula, signature

SOURCES = json.loads(
    (Path(__file__).parent / "assets/absolute-inequalities/quadratic.json").read_text()
)
KEY = "absolute_quadratic_union"
ALT = "Две квадратные ветви неравенства с модулем и их объединение"


def compatible(entry, a):
    return entry.get("branches") == [signature(s) for s in a.branches] and entry.get(
        "union"
    ) == str(a.solution)


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
    a = analyze(read_formula(context)[1], "quadratic_comparison")
    matches = [uid for uid, entry in SOURCES["figures"].items() if compatible(entry, a)]
    return tuple(
        {"source_asset_id": uid, "section_id": "solution:1", "alt_text": ALT}
        for uid in matches[:1]
    )


def diagram_specs(context):
    a = analyze(read_formula(context)[1], "quadratic_comparison")
    _, svg = selection(context, a)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def chart(context, a, generated):
    return prepare_chart(context, a, generated, key=KEY, alt=ALT, selector=selection)
