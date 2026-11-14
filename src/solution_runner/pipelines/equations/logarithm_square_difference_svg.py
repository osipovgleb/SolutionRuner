"""Adapt the parent's green/cyan/violet rows and blue intersection columns."""

import xml.etree.ElementTree as ET
from itertools import pairwise

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_labels import pieces, width
from .rational_inequality_roots import ordered
from .rational_inequality_svg import NS, hatch, label, node

WIDTH, RIGHT = 500, 484
Y = (24, 88, 152)
COLORS = ("#0A990A", "#007EA5", "#8150F9")


def intervals(value):
    if value == sp.EmptySet:
        return ()
    parts = sp.Union.make_args(value)
    if any(not isinstance(part, sp.Interval) for part in parts):
        raise UnsupportedCondition("the source composition needs interval regions")
    return tuple(sorted(parts, key=sp.default_sort_key))


def boundaries(value):
    return {
        p for part in intervals(value) for p in (part.start, part.end) if p.is_finite
    }


def axis(root, y):
    node(
        root,
        "line",
        x1=0.5,
        y1=y,
        x2=RIGHT + 8,
        y2=y,
        stroke="#000000",
        stroke_width=0.75,
    )
    node(
        root,
        "polygon",
        points=f"{RIGHT + 10},{y} {RIGHT + 1},{y - 3} {RIGHT + 4},{y} {RIGHT + 1},{y + 3}",
    )
    node(
        root,
        "text",
        x=RIGHT + 3,
        y=y + 13,
        font_family="Times New Roman,serif",
        font_style="italic",
        font_size=14,
    ).text = "x"


def bands(root, solution, positions):
    for part in intervals(solution):
        left, right = positions.get(part.start, 0.5), positions.get(part.end, RIGHT)
        node(
            root,
            "rect",
            data_intersection=str(part),
            x=left,
            y=Y[0],
            width=right - left,
            height=Y[-1] - Y[0],
            fill="#143B8F",
            fill_opacity=0.48,
        )
        for point in (part.start, part.end):
            if point.is_finite:
                node(
                    root,
                    "line",
                    x1=positions[point],
                    x2=positions[point],
                    y1=Y[0],
                    y2=Y[-1],
                    stroke="white",
                    stroke_width=1,
                    stroke_dasharray="5 4",
                )


def row(root, value, points, positions, y, color, stage=None):
    axis(root, y)
    for part in intervals(value):
        hatch(
            root,
            positions.get(part.start, 0.5),
            positions.get(part.end, RIGHT),
            y,
            color,
        )
    if stage is not None:
        coords = [0.5, *(positions[p] for p in stage.points), RIGHT]
        for index, (left, right) in enumerate(pairwise(coords)):
            node(
                root,
                "text",
                data_row_y=y,
                data_sign=stage.signs[index],
                x=(left + right) / 2,
                y=y - 10,
                text_anchor="middle",
                font_family="Times New Roman,serif",
                font_size=16,
                fill=color,
            ).text = {1: "+", -1: "−", 0: "0"}[stage.signs[index]]
    for point in points:
        x = positions[point]
        node(
            root,
            "circle",
            data_row_y=y,
            data_boundary=str(point),
            cx=x,
            cy=y,
            r=2.6924,
            fill="white",
            stroke="#000000",
            stroke_width=0.5,
        )
        if stage is None:
            node(
                root,
                "text",
                x=x,
                y=y - 9,
                text_anchor="middle",
                font_family="Times New Roman,serif",
                font_size=14,
            ).text = str(point).replace("-", "−")
        else:
            label(root, point, x, y)


def render(a, index):
    branch = a.systems[index]
    points = ordered(
        boundaries(a.domain)
        | set(branch.difference_stage.points)
        | set(branch.sum_stage.points)
    )
    if not 3 <= len(points) <= 6:
        raise UnsupportedCondition(
            "the reviewed three-row chart needs three to six aligned boundaries"
        )
    if any(p.is_Integer is not True or abs(p) > 1000 for p in boundaries(a.domain)):
        raise UnsupportedCondition(
            "the source domain row requires small integer labels"
        )
    for point in points:
        n, d = sp.fraction(sp.radsimp(sp.together(point)))
        if (
            d.is_Integer is not True
            or d <= 0
            or len(str(d)) > 8
            or width(pieces(n), 12 if d != 1 else 14) > 60
        ):
            raise UnsupportedCondition(
                "an exact label exceeds the reviewed chart column width"
            )
    positions = {
        point: 60 + i * 380 / (len(points) - 1) for i, point in enumerate(points)
    }
    root = ET.Element(
        "{" + NS + "}svg",
        {
            "width": str(WIDTH),
            "height": "194",
            "viewBox": f"0 0 {WIDTH} 194",
            "data-source-style": "0c1c1d58-2e51-4b3b-bd6e-4ddac9b40653",
            "data-system": str(index + 1),
        },
    )
    node(
        root, "title"
    ).text = f"Система {index + 1}: область определения и знаки двух множителей"
    bands(root, branch.solution, positions)
    row(root, a.domain, ordered(boundaries(a.domain)), positions, Y[0], COLORS[0])
    row(
        root,
        branch.difference_stage.solution,
        branch.difference_stage.points,
        positions,
        Y[1],
        COLORS[1],
        branch.difference_stage,
    )
    row(
        root,
        branch.sum_stage.solution,
        branch.sum_stage.points,
        positions,
        Y[2],
        COLORS[2],
        branch.sum_stage,
    )
    return ET.tostring(root, encoding="unicode")
