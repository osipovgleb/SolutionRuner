"""Retain the parent's excluded blue gap and signs only on the two domain rays."""

import json
from pathlib import Path
from xml.etree import ElementTree as ET

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .exponential_radical_product import analyze
from .radical_inequality_figures import chart as prepare_chart
from .radical_inequality_figures import selection as select_chart
from .rational_inequality_figures import read_formula
from .rational_inequality_svg import NS, node

SOURCES = json.loads(
    (
        Path(__file__).parent / "assets/exponential-inequalities/root-product.json"
    ).read_text()
)
KEY = "exponential_root_product_domain"
ALT = "Знаки произведения на области определения; синий отрезок между точками исключён"


def compatible(entry, a):
    return (
        entry.get("points") == list(map(str, a.points))
        and entry.get("signs") == list(a.signs)
        and entry.get("blue_segment") == "excluded_open_domain_gap"
    )


def render(a):
    if any(p.is_Integer is not True or abs(p) > 99 for p in a.points):
        raise UnsupportedCondition(
            "the reviewed generated source layout requires small integer domain endpoints"
        )
    root = ET.Element(
        "{" + NS + "}svg",
        width="179.1206",
        height="39.7533",
        viewBox="0 0 179.1206 39.7533",
    )
    root.set("data-source-style", "49842f5c-b83e-4560-bd87-418a6b121506")
    node(root, "title").text = ALT
    y, positions = 18.9439, (44.0009, 119.9049)
    node(
        root, "line", x1=0, x2=170.0852, y1=y, y2=y, stroke="#000000", stroke_width=1.25
    )
    node(
        root,
        "polygon",
        points="170.1146,18.9199 164.1087,14.4199 179.1206,18.9199 164.1087,23.4209",
    )
    node(
        root,
        "line",
        data_excluded_domain_gap="open",
        x1=positions[0],
        x2=119.1489,
        y1=y,
        y2=y,
        stroke="#143B8F",
        stroke_width=1.25,
    )
    for point, x in zip(a.points, positions, strict=True):
        node(
            root,
            "circle",
            data_point=point,
            data_closed="true",
            cx=x,
            cy=y,
            r=2.6929,
            stroke="#000000",
            stroke_width=0.75,
        )
        node(
            root,
            "text",
            x=x,
            y=35.55,
            text_anchor="middle",
            font_family="Times New Roman,serif",
            font_size=14,
        ).text = str(point).replace("-", "−")
    for sign, x in zip(a.signs, (22, 147), strict=True):
        node(
            root,
            "text",
            data_sign=sign,
            x=x,
            y=11.5,
            text_anchor="middle",
            font_family="Times New Roman,serif",
            font_size=16,
            fill="#143B8F",
        ).text = "−" if sign < 0 else "+"
    node(
        root,
        "text",
        x=174,
        y=31.5,
        text_anchor="middle",
        font_family="Times New Roman,serif",
        font_style="italic",
        font_size=14,
    ).text = "x"
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
