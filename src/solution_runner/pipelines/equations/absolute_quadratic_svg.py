"""Parent-sized quadratic sign rows with their union between the axes."""

from itertools import pairwise
from xml.etree import ElementTree as ET

import sympy as sp

from ..probability.common import UnsupportedCondition
from .radical_inequality_difference_svg import sign_center
from .rational_inequality_roots import ordered
from .rational_inequality_svg import NS, hatch, marker, node

TOP, BOTTOM, RIGHT = 35.303, 72.4583, 191.5109


def axis(root, y):
    node(root, "line", x1=0.5, x2=RIGHT, y1=y, y2=y, stroke="#000000", stroke_width=1)
    node(
        root,
        "polygon",
        points=f"{RIGHT - 6},{y - 3} {RIGHT + 2},{y} {RIGHT - 6},{y + 3}",
    )
    node(
        root,
        "text",
        x=RIGHT - 4,
        y=y + 13,
        font_family="Times New Roman,serif",
        font_style="italic",
        font_size=14,
    ).text = "x"


def row(root, stage, positions, y, color, name):
    group = node(root, "g", data_row=name)
    part = stage.solution
    hatch(group, positions[part.start], positions[part.end], y, color)
    axis(group, y)
    coords = [0.5, *(positions[p] for p in stage.points), RIGHT]
    for sign, (lo, hi) in zip(stage.signs, pairwise(coords), strict=True):
        node(
            group,
            "text",
            data_sign=sign,
            x=sign_center(lo, hi, sorted(positions.values())),
            y=y - 10,
            text_anchor="middle",
            font_family="Times New Roman,serif",
            font_size=16,
            fill=color,
        ).text = {-1: "−", 0: "0", 1: "+"}[sign]
    for point in stage.points:
        label_y = BOTTOM if name == "second" else TOP - 30 if point.is_Integer else -1.7
        marker(group, point, positions[point], y, True, label_y=label_y)


def render(a):
    points = ordered({p for stage in a.branches for p in stage.points})
    if (
        not 2 <= len(points) <= 4
        or any(p.is_Rational is not True or abs(p.p) > 9 or p.q > 9 for p in points)
        or not isinstance(a.solution, sp.Interval)
    ):
        raise UnsupportedCondition(
            "the reviewed union chart needs two to four small rational boundaries"
        )
    positions = {p: 26 + i * 124 / (len(points) - 1) for i, p in enumerate(points)}
    root = ET.Element(
        "{" + NS + "}svg",
        width="194.431",
        height="104.525",
        viewBox="0 0 194.431 104.525",
    )
    root.set("data-source-style", "41b27b92-fd8f-47cd-b986-0313a2ab8db8")
    node(
        root, "title"
    ).text = "Две квадратные ветви неравенства с модулем и их объединение"
    lo, hi = positions[a.solution.start], positions[a.solution.end]
    node(
        root,
        "rect",
        data_union=str(a.solution),
        x=lo,
        y=TOP,
        width=hi - lo,
        height=BOTTOM - TOP,
        fill="#143B8F",
        opacity=0.5,
    )
    for point in (a.solution.start, a.solution.end):
        node(
            root,
            "line",
            x1=positions[point],
            x2=positions[point],
            y1=TOP,
            y2=BOTTOM,
            stroke="#143B8F",
            stroke_width=0.75,
            stroke_dasharray="6.4285,2.5714",
        )
    row(root, a.branches[0], positions, TOP, "#0A990A", "first")
    row(root, a.branches[1], positions, BOTTOM, "#007EA5", "second")
    return ET.tostring(root, encoding="unicode")
