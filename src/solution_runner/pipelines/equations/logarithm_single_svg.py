"""Parent green sign row, cyan domain row and blue intersection columns."""

import xml.etree.ElementTree as ET
from itertools import pairwise

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_square_difference_svg import axis, boundaries, intervals
from .rational_inequality_labels import pieces, width
from .rational_inequality_roots import ordered
from .rational_inequality_svg import NS, hatch, marker, node

RIGHT = 484
TOP, BOTTOM = 38, 114


def bands(root, solution, positions):
    for part in intervals(solution):
        left, right = positions.get(part.start, 0.5), positions.get(part.end, RIGHT)
        node(
            root,
            "rect",
            data_intersection=str(part),
            x=left,
            y=TOP,
            width=right - left,
            height=BOTTOM - TOP,
            fill="#143B8F",
            opacity="0.5",
        )
        for point in (part.start, part.end):
            if point.is_finite:
                node(
                    root,
                    "line",
                    x1=positions[point],
                    x2=positions[point],
                    y1=TOP,
                    y2=BOTTOM,
                    stroke="#143B8F",
                    stroke_width="0.5",
                    stroke_dasharray="6.4285,2.5714",
                )


def row(root, value, points, positions, y, color, stage=None):
    group = node(root, "g", data_row="stage" if stage is not None else "domain")
    axis(group, y)
    for part in intervals(value):
        hatch(
            group,
            positions.get(part.start, 0.5),
            positions.get(part.end, RIGHT),
            y,
            color,
        )
    if stage is not None:
        coords = [0.5, *(positions[p] for p in stage.points), RIGHT]
        for index, (left, right) in enumerate(pairwise(coords)):
            node(
                group,
                "text",
                data_sign=stage.signs[index],
                x=(left + right) / 2,
                y=y - 10,
                text_anchor="middle",
                font_family="Times New Roman,serif",
                font_size=16,
                fill=color,
            ).text = {1: "+", -1: "−", 0: "0"}[stage.signs[index]]
    for point in points:
        label_y = y if stage is None else y - 31 if point.is_Integer else y - 40
        marker(
            group,
            point,
            positions[point],
            y,
            value.contains(point) is sp.true,
            label_y=label_y,
        )


def render(a):
    stage = a.product
    points = ordered(set(stage.points) | boundaries(a.domain))
    if not 2 <= len(points) <= 8:
        raise UnsupportedCondition(
            "the reviewed two-row chart needs two to eight aligned boundaries"
        )
    for p in points:
        n, d = sp.fraction(sp.radsimp(sp.together(p)))
        if (
            d.is_Integer is not True
            or d <= 0
            or width(pieces(n), 12 if d != 1 else 14) > 55
        ):
            raise UnsupportedCondition(
                "an exact chart label exceeds the reviewed column width"
            )
    positions = {p: 45 + i * 390 / (len(points) - 1) for i, p in enumerate(points)}
    root = ET.Element(
        "{" + NS + "}svg",
        {
            "width": "500",
            "height": "155",
            "viewBox": "0 0 500 155",
            "data-source-style": "56bd8c04-3d80-4497-a6e0-1567a62e0526",
        },
    )
    node(
        root, "title"
    ).text = "Рационализированное неравенство, область определения и их пересечение"
    bands(root, a.solution, positions)
    row(root, stage.solution, stage.points, positions, TOP, "#0A990A", stage)
    row(root, a.domain, ordered(boundaries(a.domain)), positions, BOTTOM, "#007EA5")
    return ET.tostring(root, encoding="unicode")
