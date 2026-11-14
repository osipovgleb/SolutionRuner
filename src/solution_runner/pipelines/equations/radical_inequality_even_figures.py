"""Reuse exact projected sign charts, independently of the later root-domain cut."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from ..probability import solution_diagrams
from .radical_inequality_even_power import analyze
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .rational_inequality_figures import read_formula, signature
from .rational_inequality_svg import NS, render_single

SOURCES = json.loads(
    (Path(__file__).parent / "assets/radical-inequalities/even-power.json").read_text()
)
KEY = "radical_even_power_sign_chart"
ALT = "Метод интервалов после замены квадрата корня с сохранением исходных исключений"


def compatible(entry, a):
    return entry.get("stage") == signature(a.stage)


def render(a):
    root = ET.fromstring(
        render_single(a.stage, layout="radical_single", fraction_label_offset=8)
    )
    root.set("data-source-style", "b113407d-cfad-4010-9a7d-54a053b6e0dc")
    root.find("{" + NS + "}title").text = ALT
    return ET.tostring(root, encoding="unicode")


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
