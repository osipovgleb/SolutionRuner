"""Parent-sized two-row sign chart with fraction labels above its upper axis."""

from itertools import pairwise
from xml.etree import ElementTree as ET

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_square_difference_svg import boundaries, intervals
from .rational_inequality_roots import ordered
from .rational_inequality_svg import NS, hatch, marker, node

TOP, BOTTOM, RIGHT = 35.7203, 72.8756, 244.1596


def axis(root, y):
    node(root, "line", x1=0.5, x2=RIGHT, y1=y, y2=y, stroke="#000000", stroke_width=1)
    node(
        root,
        "polygon",
        points=f"244.152,{y} 238.1461,{y - 4.5} 253.1598,{y} 238.1461,{y + 4.5}",
    )
    node(
        root,
        "text",
        x=RIGHT - 1,
        y=y + 13,
        font_family="Times New Roman,serif",
        font_style="italic",
        font_size=14,
    ).text = "x"


def sign_center(lo, hi, guides):
    middle = (lo + hi) / 2
    if all(abs(middle - x) >= 12 for x in guides):
        return middle
    cuts = [lo, *(x for x in guides if lo < x < hi), hi]
    candidates = [(a + b) / 2 for a, b in pairwise(cuts) if b - a >= 24]
    if not candidates:
        raise UnsupportedCondition("a sign label would overlap the intersection guides")
    return min(candidates, key=lambda x: abs(x - middle))


def row(root, stage, positions, y, color, name):
    group = node(root, "g", data_row=name)
    for part in intervals(stage.solution):
        hatch(
            group,
            positions.get(part.start, 0.5),
            positions.get(part.end, RIGHT),
            y,
            color,
        )
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
    for p in stage.points:
        label_y = y if name == "domain" else TOP - 27 if p.is_Integer else 1.5
        marker(
            group,
            p,
            positions[p],
            y,
            stage.solution.contains(p) is sp.true,
            label_y=label_y,
        )


def render(a):
    points = ordered(set(a.stage.points) | boundaries(a.other_stage.solution))
    if not 2 <= len(points) <= 6 or any(
        p.is_Rational is not True or abs(p.p) > 99 or p.q > 20 for p in points
    ):
        raise UnsupportedCondition(
            "the reviewed generated chart requires bounded rational labels; exact native surd charts must be reused"
        )
    positions = {p: 40 + i * 170 / (len(points) - 1) for i, p in enumerate(points)}
    root = ET.Element(
        "{" + NS + "}svg",
        width="253.1598",
        height="93.5393",
        viewBox="0 0 253.1598 93.5393",
    )
    root.set("data-source-style", "b35c98e3-4bcd-4927-8022-b264f999ba29")
    node(
        root, "title"
    ).text = "Рациональное неравенство, область определения корней и пересечение"
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
    row(root, a.stage, positions, TOP, "#0A990A", "stage")
    row(root, a.other_stage, positions, BOTTOM, "#007EA5", "domain")
    return ET.tostring(root, encoding="unicode")
