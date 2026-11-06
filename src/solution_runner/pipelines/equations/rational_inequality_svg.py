"""Adapt the reviewed single-axis and two-axis rational sign-chart compositions."""

import xml.etree.ElementTree as ET
from itertools import pairwise

import sympy as sp

from .rational_inequality import accepts
from .rational_inequality_labels import label as algebraic_label
from .rational_inequality_parser import X

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
DIVISION_LAYOUTS = {
    "division_single": (217.7959, 39.694),
    "degree_single": (252.0512, 39.689),
    "split_single": (206.6025, 50.3737),
}

TOP, BOTTOM = 27.4235, 65.3395
LEFT, RIGHT = 0.5, 184.938


def node(parent, tag, **attrs):
    return ET.SubElement(
        parent,
        "{" + NS + "}" + tag,
        {k.replace("_", "-"): str(v) for k, v in attrs.items()},
    )


def label(root, point, x, y):
    if point.is_Rational is not True:
        algebraic_label(root, point, x, y)
        return
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


def marker(root, point, x, y, closed, *, label_y=None):
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
    label(root, point, x, y if label_y is None else label_y)


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
    height = 101 if any(point.is_Integer is not True for point in a.points) else 86.2442
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


def single_canvas(width, height, layout, variable):
    y = 18.928
    root = ET.Element(
        "{" + NS + "}svg",
        {
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
        },
    )
    node(root, "title").text = "Метод интервалов с сохранением исключённых точек"
    node(
        root,
        "line",
        x1=0,
        y1=y,
        x2=207.8005,
        y2=y,
        fill="none",
        stroke="#000000",
        stroke_width=1.25,
        stroke_linejoin="round",
        stroke_miterlimit=8,
    )
    node(
        root,
        "polygon",
        points="206.3005,18.904 200.2945,14.404 215.3065,18.904 200.2945,23.405",
    )
    node(
        root,
        "text",
        x=206,
        y=32.5,
        font_family="Times New Roman,serif",
        font_style="italic",
        font_size=14,
    ).text = variable
    if layout == "vieta":
        for item in root:
            if item.tag.endswith("line"):
                item.set("x2", "206.7561")
            elif item.tag.endswith("polygon"):
                item.set(
                    "points",
                    "205.2561,18.904 199.2501,14.404 214.2621,18.904 199.2501,23.405",
                )
            elif item.tag.endswith("text"):
                item.set("x", "205")
    if layout in DIVISION_LAYOUTS:
        delta = width - 215.3065
        for item in root:
            if item.tag.endswith("line"):
                item.set("x2", str(207.8005 + delta))
            elif item.tag.endswith("polygon"):
                item.set(
                    "points",
                    f"{206.3005 + delta},18.904 {200.2945 + delta},14.404 {width},18.904 {200.2945 + delta},23.405",
                )
            elif item.tag.endswith("text"):
                item.set("x", str(206 + delta))
    return root


def render_single(a, *, layout="single", variable="x"):
    if not 1 <= len(a.points) <= 6:
        raise ValueError("the reviewed single chart needs one to six boundaries")
    width = 214.2621 if layout == "vieta" else 215.3065
    height = {"vieta": 44.9037, "radical_single": 50.9612}.get(
        layout, 39.6595 if all(p.is_Integer is True for p in a.points) else 54.6595
    )
    if layout in DIVISION_LAYOUTS:
        width, base_height = DIVISION_LAYOUTS[layout]
        height = max(
            base_height,
            54.6595 if any(p.is_Integer is not True for p in a.points) else base_height,
        )
    y = 18.928
    root = single_canvas(width, height, layout, variable)
    positions = [
        37.5135 + i * (164.5463 - 37.5135) / max(1, len(a.points) - 1)
        for i in range(len(a.points))
    ]
    if len(a.points) == 4:
        positions = [37.5135, 76.7436, 119.2145, 164.5463]
    if len(a.points) == 1:
        positions = [107.65]
    if layout in DIVISION_LAYOUTS:
        positions = [x * width / 215.3065 for x in positions]
    end = width - 9.006 if layout in DIVISION_LAYOUTS else 206.3005
    for index, (left, right) in enumerate(pairwise([0, *positions, end])):
        node(
            root,
            "text",
            data_interval=index,
            data_sign=a.signs[index],
            x=(left + right) / 2,
            y=10,
            text_anchor="middle",
            font_family="Times New Roman,serif",
            font_size=16,
            fill="#143B8F",
        ).text = {-1: "−", 0: "0", 1: "+"}[a.signs[index]]
    for point, x in zip(a.points, positions):
        marker(
            root,
            point,
            x,
            y,
            point not in a.poles and a.sign_operator.endswith("="),
            label_y=(
                y + 4
                if (
                    variable != "x"
                    or layout == "polynomial_single"
                    or layout in DIVISION_LAYOUTS
                )
                and point.is_Rational is True
                and not point.is_Integer
                else 16.5
                if point.is_Rational is True
                else y
            ),
        )
    return ET.tostring(root, encoding="unicode")
