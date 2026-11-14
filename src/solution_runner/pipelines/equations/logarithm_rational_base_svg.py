"""Parent green/cyan/violet rows with aligned blue intersection columns."""

import xml.etree.ElementTree as ET

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_single_svg import row
from .logarithm_square_difference_svg import boundaries, intervals
from .rational_inequality_labels import pieces, width
from .rational_inequality_roots import ordered
from .rational_inequality_svg import NS, node

COLORS = ("#0A990A", "#007EA5", "#8150F9")


def signature(case):
    result = []
    for value, stage in zip(case.values, case.stages, strict=True):
        points = ordered(
            boundaries(value) | (set(stage.points) if stage is not None else set())
        )
        result.append(
            {
                "values": str(value),
                "points": list(map(str, points)),
                "closed": [bool(value.contains(p)) for p in points],
                "signs": list(stage.signs) if stage is not None else None,
                "expression": str(stage.original) if stage is not None else None,
                "operator": stage.operator if stage is not None else None,
            }
        )
    return {"sign": case.sign, "rows": result, "intersection": str(case.solution)}


def render(case):
    rows = signature(case)["rows"]
    points = ordered(
        set().union(
            *(boundaries(v) for v in case.values),
            *(set(s.points) for s in case.stages if s is not None),
        )
    )
    if not 2 <= len(points) <= 8:
        raise UnsupportedCondition(
            "the parent systems need two to eight aligned boundaries"
        )
    for point in points:
        n, d = sp.fraction(sp.radsimp(sp.together(point)))
        if (
            d.is_Integer is not True
            or d <= 0
            or width(pieces(n), 12 if d != 1 else 14) > 55
        ):
            raise UnsupportedCondition(
                "an exact chart label exceeds the reviewed column width"
            )
    positions = {p: 48 + i * 390 / (len(points) - 1) for i, p in enumerate(points)}
    ys = tuple(42 + i * 78 for i in range(len(rows)))
    root = ET.Element(
        "{" + NS + "}svg",
        {
            "width": "500",
            "height": str(ys[-1] + 42),
            "viewBox": f"0 0 500 {ys[-1] + 42}",
            "data-source-style": "507893-base-cases",
            "data-case": str(case.sign),
        },
    )
    node(root, "title").text = "Условия случая и их пересечение"
    for part in intervals(case.solution):
        left, right = positions.get(part.start, 0.5), positions.get(part.end, 484)
        node(
            root,
            "rect",
            data_intersection=str(part),
            x=left,
            y=ys[0],
            width=right - left,
            height=ys[-1] - ys[0],
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
                    y1=ys[0],
                    y2=ys[-1],
                    stroke="#143B8F",
                    stroke_width="0.5",
                    stroke_dasharray="6.4285,2.5714",
                )
    for index, (value, stage, y) in enumerate(
        zip(case.values, case.stages, ys, strict=True)
    ):
        group = node(root, "g", data_row_index=index)
        marks = ordered(
            boundaries(value) | (set(stage.points) if stage is not None else set())
        )
        row(group, value, marks, positions, y, COLORS[index], stage)
    return ET.tostring(root, encoding="unicode")
