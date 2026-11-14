"""The radical parent's green/cyan rows with blue intersection columns."""

from itertools import pairwise
from xml.etree import ElementTree as ET

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_square_difference_svg import boundaries, intervals
from .rational_inequality_roots import ordered
from .rational_inequality_svg import NS, hatch, marker, node

TOP, BOTTOM, RIGHT = 22.4868, 59.6422, 233.2744


def axis(root, y):
    node(
        root,
        "line",
        x1=0.5,
        x2=234.7753,
        y1=y,
        y2=y,
        stroke="#000000",
        stroke_width=0.75,
    )
    node(
        root,
        "polygon",
        points=f"233.2744,{y} 227.2685,{y - 4.5} 242.2822,{y} 227.2685,{y + 4.5}",
    )
    node(
        root,
        "text",
        x=233,
        y=y + 13,
        font_family="Times New Roman,serif",
        font_style="italic",
        font_size=14,
    ).text = "x"


def render(a):
    points = ordered(set(a.stage.points) | boundaries(a.domain))
    if not 2 <= len(points) <= 6 or any(p.is_Integer is not True for p in points):
        raise UnsupportedCondition(
            "the root comparison chart needs two to six integer boundaries"
        )
    positions = {p: 40 + i * 160 / (len(points) - 1) for i, p in enumerate(points)}
    root = ET.Element(
        "{" + NS + "}svg",
        width="242.2822",
        height="83.2424",
        viewBox="0 0 242.2822 83.2424",
    )
    root.set("data-source-style", "652fe099-f167-4deb-81c6-c0327f1d1731")
    node(root, "title").text = "Неравенство с радикалами и пересечение с ограничениями"
    for part in intervals(a.solution):
        lo, hi = positions.get(part.start, 0.5), positions.get(part.end, RIGHT)
        node(
            root,
            "rect",
            data_intersection=str(part),
            x=lo,
            y=TOP,
            width=hi - lo,
            height=BOTTOM - TOP,
            fill="#143B8F",
            opacity=0.5,
        )
        for p in (part.start, part.end):
            if p.is_finite:
                node(
                    root,
                    "line",
                    x1=positions[p],
                    x2=positions[p],
                    y1=TOP,
                    y2=BOTTOM,
                    stroke="#143B8F",
                    stroke_width=0.75,
                    stroke_dasharray="6.4285,2.5714",
                )
    for value, row_points, y, color, name in (
        (a.stage.solution, a.stage.points, TOP, "#0A990A", "stage"),
        (a.domain, ordered(boundaries(a.domain)), BOTTOM, "#007EA5", "domain"),
    ):
        group = node(root, "g", data_row=name)
        for part in intervals(value):
            hatch(
                group,
                positions.get(part.start, 0.5),
                positions.get(part.end, RIGHT),
                y,
                color,
            )
        axis(group, y)
        for p in row_points:
            marker(
                group,
                p,
                positions[p],
                y,
                value.contains(p) is sp.true,
                label_y=y - 27 if name == "stage" else y,
            )
        if name == "stage":
            coords = [0.5, *(positions[p] for p in row_points), RIGHT]
            for sign, (lo, hi) in zip(a.stage.signs, pairwise(coords), strict=True):
                node(
                    group,
                    "text",
                    data_sign=sign,
                    x=(lo + hi) / 2,
                    y=y - 10,
                    text_anchor="middle",
                    font_family="Times New Roman,serif",
                    font_size=16,
                    fill=color,
                ).text = {-1: "−", 0: "0", 1: "+"}[sign]
    return ET.tostring(root, encoding="unicode")
