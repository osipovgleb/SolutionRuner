"""One source-chart contract for the two nonnegative-factor presentations."""

import json
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .radical_inequality_factor import analyze
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .radical_inequality_svg import BOTTOM, RIGHT
from .radical_inequality_svg import render as intersection_svg
from .rational_inequality_figures import read_formula, signature
from .rational_inequality_svg import NS, node, render_single
from .rational_substitution_preimages import comparison

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/radical-inequalities/nonnegative-factor.json"
    ).read_text()
)
KEY = "radical_nonnegative_factor_chart"
ALT = "Знаки рационального коэффициента при сохранённых исходных ограничениях"


def compatible(entry, a):
    return (
        entry.get("method") == a.method
        and entry.get("stage") == signature(a.stage)
        and (
            a.method == "squared_quotient"
            or (
                entry.get("domain") == str(a.constraints.roots)
                and entry.get("intersection") == str(a.solution)
            )
        )
    )


def render(a):
    if a.method == "squared_quotient":
        root = ET.fromstring(render_single(a.stage, layout="radical_single"))
        source = "45d2d373-83fa-49dc-a954-115dba252fec"
    else:
        if a.stage.solution.intersect(a.constraints.roots) != a.solution:
            raise UnsupportedCondition(
                "the parent intersection chart must include every zero-factor solution"
            )
        view = SimpleNamespace(
            stage=a.stage, domain=a.constraints.roots, solution=a.solution
        )
        root = ET.fromstring(intersection_svg(view))
        group = root.find("{" + NS + '}g[@data-row="domain"]')
        markers = group.findall("{" + NS + "}circle")
        coords = [0.5, *(float(m.get("cx")) for m in markers), RIGHT]
        signs = comparison(a.numerator, ">=").signs
        for sign, (lo, hi) in zip(signs, pairwise(coords), strict=True):
            node(
                group,
                "text",
                data_sign=sign,
                x=(lo + hi) / 2,
                y=BOTTOM - 10,
                text_anchor="middle",
                font_family="Times New Roman,serif",
                font_size=16,
                fill="#007EA5",
            ).text = {-1: "−", 0: "0", 1: "+"}[sign]
        source = "87a18f54-bf62-4452-b902-1b2a48c260a2"
    root.set("data-source-style", source)
    root.find("{http://www.w3.org/2000/svg}title").text = ALT
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
    matches = [uid for uid, entry in SOURCES["figures"].items() if compatible(entry, a)]
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
