"""Adapt the parent's four-point hatching and double-multiplicity captions."""

import xml.etree.ElementTree as ET

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_exponential_figures import multiplicity
from .rational_inequality_hatched_svg import signed_intervals
from .rational_inequality_labels import pieces, width
from .rational_inequality_svg import marker, node, single_canvas


def render(a):
    n, d = sp.fraction(a.expression)
    if len(a.points) != 4 or len(a.zeros) != 2 or len(a.poles) != 2:
        raise UnsupportedCondition(
            "the source composition requires four distinct boundaries"
        )
    orders = {p: multiplicity(n, p) for p in a.zeros} | {
        p: multiplicity(d, p) for p in a.poles
    }
    if sorted(orders[p] for p in a.zeros) != [1, 2] or any(
        orders[p] != 2 for p in a.poles
    ):
        raise UnsupportedCondition(
            "the reviewed chart needs one double zero and two double poles"
        )
    fractional = False
    for point in a.points:
        numerator, denominator = sp.fraction(sp.radsimp(sp.together(point)))
        if denominator.is_Integer is not True or denominator <= 0 or denominator > 99:
            raise UnsupportedCondition(
                "the source labels need small positive integer denominators"
            )
        if width(pieces(numerator), 14) > 38:
            raise UnsupportedCondition(
                "the exact label exceeds the reviewed source column width"
            )
        fractional |= denominator != 1
    canvas_width = 298.669
    height = 67.811 if fractional else 51.811
    y = 18.928
    positions = [53.75, 106.75, 166.25, 221.25]
    root = single_canvas(canvas_width, height, "hatched_square", "x")
    signed_intervals(root, a, positions, canvas_width, y)
    for point, x in zip(a.points, positions):
        marker(
            root, point, x, y, point not in a.poles and a.sign_operator.endswith("=")
        )
        if orders[point] == 2:
            node(
                root,
                "text",
                data_multiplicity=2,
                **(
                    {"data_pole": str(point)}
                    if point in a.poles
                    else {"data_zero": str(point)}
                ),
                x=x if fractional else x + 6,
                y=61.5 if fractional else 39.5,
                text_anchor="middle" if fractional else "start",
                font_family="Times New Roman,serif",
                font_size=8.5,
                fill="#000000",
            ).text = "кратн. 2"
    return ET.tostring(root, encoding="unicode")
