"""Adapt the reviewed single-axis and two-axis rational sign-chart compositions."""

import xml.etree.ElementTree as ET
from itertools import pairwise

import sympy as sp

from .rational_inequality import accepts
from .rational_inequality_parser import X

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
TOP, BOTTOM = 27.4235, 65.3395
LEFT, RIGHT = 0.5, 184.938


def node(parent, tag, **attrs):
    return ET.SubElement(
        parent,
        "{" + NS + "}" + tag,
        {k.replace("_", "-"): str(v) for k, v in attrs.items()},
    )


def label(root, point, x, y):
    common = {
        "x": x,
        "text_anchor": "middle",
        "font_family": "Times New Roman,serif",
        "font_size": 14,
        "fill": "#000000",
    }
    if point.q == 1:
        node(root, "text", y=y + 18, **common).text = str(point).replace("-", "−")
        return
    width = max(len(str(abs(point.p))), len(str(point.q))) * 7 + 2
    node(root, "text", y=y + 13, **common).text = str(abs(point.p))
    node(root, "text", y=y + 28, **common).text = str(point.q)
    node(
        root,
        "line",
        x1=x - width / 2,
        x2=x + width / 2,
        y1=y + 16,
        y2=y + 16,
        stroke="#000000",
        stroke_width=0.6,
    )
    if point < 0:
        node(root, "text", y=y + 21, **{**common, "x": x - width / 2 - 6}).text = "−"


def axis(root, y):
    node(
        root,
        "line",
        x1=LEFT,
        x2=190.5937,
        y1=y,
        y2=y,
        stroke="#000000",
        stroke_width=0.75,
        stroke_linecap="round",
    )
    node(
        root,
        "polygon",
        points=f"184.938,{y} 178.9322,{y - 4.5} 193.9458,{y} 178.9322,{y + 4.5}",
    )
    node(
        root,
        "text",
        x=184,
        y=y + 13,
        font_family="Times New Roman,serif",
        font_style="italic",
        font_size=14,
    ).text = "x"


def marker(root, point, x, y, closed):
    node(
        root,
        "circle",
        data_boundary=str(point),
        cx=x,
        cy=y,
        r=2.6924,
        fill="#000000" if closed else "#FFFFFF",
        stroke="#000000",
        stroke_width=0.5,
    )
    label(root, point, x, y)


def hatch(root, left, right, y, color, *, reverse=False):
    x = left + 0.5
    while x + 4.256 <= right:
        node(
            root,
            "line",
            x1=x,
            x2=x + 4.256,
            y1=y - 4.56 if reverse else y,
            y2=y if reverse else y - 4.56,
            stroke=color,
            stroke_width=0.75,
        )
        x += 3.34


def render(a, *, double=False):
    if not 1 <= len(a.points) <= 6 or (double and not a.holes):
        raise ValueError(
            "the reviewed chart needs one to six boundaries and its domain row"
        )
    height = 101 if any(point.q != 1 for point in a.points) else 86.2442
    if not double:
        height -= BOTTOM - TOP
    root = ET.Element(
        "{" + NS + "}svg",
        {
            "width": "193.9458",
            "height": str(height),
            "viewBox": f"0 0 193.9458 {height}",
        },
    )
    node(root, "title").text = "Метод интервалов с ограничениями исходных знаменателей"
    positions = {
        p: 42.4849 + i * (150.5537 - 42.4849) / max(1, len(a.points) - 1)
        for i, p in enumerate(a.points)
    }
    if len(a.points) == 1:
        positions[a.points[0]] = 96.97
    top_points = tuple(p for p in a.points if not double or p not in a.holes)
    boundaries = (-sp.oo, *top_points, sp.oo)
    color = "#0A990A" if double else "#143B8F"
    # Domain holes keep their position in both rows, without inventing a sign change.
    for index, (lo, hi) in enumerate(pairwise(boundaries)):
        left, right = positions.get(lo, LEFT), positions.get(hi, RIGHT)
        sample = hi - 1 if lo == -sp.oo else lo + 1 if hi == sp.oo else (lo + hi) / 2
        sign = int(sp.sign(a.expression.subs(X, sample)))
        node(
            root,
            "text",
            data_interval=index,
            data_sign=sign,
            x=(left + right) / 2,
            y=TOP - 10,
            text_anchor="middle",
            font_family="Times New Roman,serif",
            font_size=16,
            fill=color,
        ).text = {1: "+", -1: "−", 0: "0"}[sign]
        if double and accepts(sp.Integer(sign), a.sign_operator):
            node(
                root,
                "rect",
                data_selected_interval=index,
                x=left,
                y=TOP,
                width=right - left,
                height=BOTTOM - TOP,
                fill="#143B8F",
                opacity=0.5,
            )
            hatch(root, left, right, TOP, color)
    axis(root, TOP)
    for point in a.points:
        if not double or point not in a.holes:
            marker(
                root,
                point,
                positions[point],
                TOP,
                point not in a.poles and a.sign_operator.endswith("="),
            )
    if double:
        domain_row(root, a, positions)
    return ET.tostring(root, encoding="unicode")


def domain_row(root, a, positions):
    domain_bounds = [LEFT, *(positions[p] for p in a.holes), RIGHT]
    for left, right in pairwise(domain_bounds):
        hatch(
            root,
            left,
            right,
            BOTTOM,
            "#007EA5",
            reverse=right <= positions[a.holes[0]],
        )
    axis(root, BOTTOM)
    for point in a.holes:
        x = positions[point]
        node(
            root,
            "line",
            data_excluded=str(point),
            x1=x,
            x2=x,
            y1=TOP,
            y2=BOTTOM,
            stroke="#143B8F",
            stroke_width=0.75,
            stroke_dasharray="2 2",
        )
        marker(root, point, x, BOTTOM, False)
