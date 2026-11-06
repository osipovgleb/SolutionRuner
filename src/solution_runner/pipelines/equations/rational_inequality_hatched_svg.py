"""Preserve selected-interval hatching and the source double-zero annotation."""

import xml.etree.ElementTree as ET
from itertools import pairwise

from ..probability.common import UnsupportedCondition
from .rational_inequality import accepts
from .rational_inequality_parser import X, polynomial
from .rational_inequality_svg import hatch, marker, node, single_canvas


def double_zero(a):
    numerator = a.expression.as_numer_denom()[0]
    p = polynomial(numerator)
    repeated = [
        r for r in a.zeros if p.diff().eval(r) == 0 and p.diff().diff().eval(r) != 0
    ]
    if (
        len(a.points) != 4
        or len(a.poles) != 2
        or len(a.zeros) != 2
        or len(repeated) != 1
        or any(p.is_Rational is not True for p in a.points)
    ):
        raise UnsupportedCondition(
            "the hatched source layout needs two rational zeros, one double, and two poles"
        )
    return repeated[0]


def signed_intervals(root, a, positions, width, y):
    for index, (left, right) in enumerate(pairwise([0, *positions, width - 9.006])):
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
        ).text = {1: "+", -1: "−", 0: "0"}[a.signs[index]]
        if accepts(a.signs[index], a.sign_operator):
            group = node(root, "g", data_selected_interval=index)
            hatch(group, left, right, y, "#143B8F")


def render(a):
    repeated = double_zero(a)
    width = 236.3568
    y = 18.928
    positions = [38.43, 94.0, 157.5, 189.0]
    repeated_index = a.points.index(repeated)
    height = 54.6595
    root = single_canvas(width, height, "hatched_square", "x")
    signed_intervals(root, a, positions, width, y)
    for point, x in zip(a.points, positions):
        marker(
            root,
            point,
            x,
            y,
            point not in a.poles and a.sign_operator.endswith("="),
            label_y=y + 4 if not point.is_Integer else 16.5,
        )
    caption_x = (
        positions[repeated_index] + 10
        if repeated_index == 0
        else positions[repeated_index]
    )
    node(
        root,
        "text",
        data_multiplicity=2,
        data_zero=str(repeated),
        x=caption_x,
        y=y + 32,
        text_anchor="start" if repeated_index == 0 else "middle",
        font_family="Times New Roman,serif",
        font_size=10,
        fill="#000000",
    ).text = "кратн. 2"
    return ET.tostring(root, encoding="unicode")


def cubic_points(a):
    if len(a.zeros) != 1 or len(a.poles) != 1 or len(a.points) != 2:
        raise UnsupportedCondition(
            "the cubic chart needs one distinct zero and one pole"
        )
    numerator, denominator = a.expression.as_numer_denom()
    zero, pole = a.zeros[0], a.poles[0]
    if (
        any(p.is_Rational is not True for p in a.points)
        or polynomial(numerator).degree() != 3
        or polynomial(denominator).degree() != 2
        or any(polynomial(numerator).diff((X, k)).eval(zero) != 0 for k in (1, 2))
        or polynomial(denominator).diff().eval(pole) != 0
    ):
        raise UnsupportedCondition("the chart requires a triple zero and a double pole")
    return zero, pole


def render_cubic(a):
    zero, pole = cubic_points(a)
    width, height, y = 174.669, 63.377, 18.928
    positions = [54.0, 111.0]
    root = single_canvas(width, height, "hatched_cube", "x")
    signed_intervals(root, a, positions, width, y)
    for point, x in zip(a.points, positions):
        marker(
            root,
            point,
            x,
            y,
            point != pole and a.sign_operator.endswith("="),
            label_y=y + 4 if not point.is_Integer else 16.5,
        )
        node(
            root,
            "text",
            data_multiplicity=3 if point == zero else 2,
            **(
                {"data_zero": str(point)}
                if point == zero
                else {"data_pole": str(point)}
            ),
            x=x + 8 if point.is_Integer else x + 10,
            y=y + 25 if point.is_Integer else y + 41,
            text_anchor="start",
            font_family="Times New Roman,serif",
            font_size=8,
            fill="#000000",
        ).text = "кр. 3" if point == zero else "кр. 2"
    return ET.tostring(root, encoding="unicode")
