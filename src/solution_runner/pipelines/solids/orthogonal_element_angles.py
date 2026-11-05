"""Prove equilateral or right-isosceles angles and preserve tangent constructions."""

import re
from itertools import combinations

import sympy as sp

from ..core.errors import ContentPlanError
from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import value
from .orthogonal_element_geometry import POINT, squared
from .orthogonal_element_terms import components, edge_row, name, square_terms


def side_rows(m, a, b):
    parts = components(m, a, b)
    label = a + b + "^2"
    return line(label + "=" + square_terms(m, parts)) + line(
        label
        + "="
        + square_terms(m, parts, numeric=True)
        + "="
        + value(squared(m.points, a + b))
    )


def angle(m, picture):
    sides = tuple(combinations(m.names, 2))
    html = (
        "<p>Рассмотрим треугольник "
        + name(m.requested)
        + ". Найдём квадраты его сторон по отмеченным размерам и теореме Пифагора:</p>"
        + picture
    )
    html += "".join(side_rows(m, a, b) for a, b in sides)
    if m.method == "equilateral":
        lengths = [squared(m.points, a + b) for a, b in sides]
        if len(set(lengths)) != 1 or m.value != 60:
            raise ContentPlanError(
                "the three actual face diagonals do not form an equilateral triangle"
            )
        html += "<p>Все три стороны равны, так как их квадраты равны. Следовательно, треугольник равносторонний, а каждый его угол равен 60°:</p>"
        html += line("=".join(a + b for a, b in sides))
    else:
        a, b = (n for n in m.names if n != m.right)
        first, second = m.right + a, m.right + b
        if squared(m.points, first) != squared(m.points, second) or m.value != 45:
            raise ContentPlanError("the actual perpendicular legs are not equal")
        html += (
            "<p>Отрезки "
            + name(first)
            + " и "
            + name(second)
            + " перпендикулярны, поскольку все двугранные углы тела прямые. Их длины равны, поэтому треугольник прямоугольный и равнобедренный, а каждый его острый угол равен 45°:</p>"
        )
        html += line(first + "=" + second)
    return html + line(r"\angle " + m.requested + "=" + value(m.value) + r"^\circ")


def tangent(m, picture):
    a, b, c = m.names
    right = m.right
    introduction = "<p>"
    if right == "K":
        opposite = "K" + c
        adjacent = b + "K"
        introduction += (
            "Опустим перпендикуляр "
            + name(c + "K")
            + " на отрезок "
            + name(a + b)
            + ". Угол "
            + name(m.requested)
            + " равен углу "
            + name("K" + b + c)
            + ". "
        )
    else:
        opposite = right + (c if right == a else a)
        adjacent = b + right
    triangle = "K" + b + c if right == "K" else m.requested
    introduction += (
        "В треугольнике "
        + name(triangle)
        + " прямой угол при вершине "
        + name(right)
        + ". Тангенс острого угла равен отношению противолежащего катета к прилежащему.</p>"
    )
    op, ad = sp.sqrt(squared(m.points, opposite)), sp.sqrt(squared(m.points, adjacent))
    if sp.simplify(op / ad - m.value) != 0:
        raise ContentPlanError(
            "the parent tangent ratio differs from the requested angle"
        )
    label = r"\tg\angle " + m.requested
    op_names = re.findall(POINT, opposite)
    ad_names = re.findall(POINT, adjacent)
    return (
        introduction
        + picture
        + edge_row(m, *op_names)
        + edge_row(m, *ad_names)
        + "<p>Подставим найденные длины катетов в отношение:</p>"
        + line(label + r"=\frac{" + opposite + "}{" + adjacent + "}")
        + line(label + r"=\frac{" + value(op) + "}{" + value(ad) + "}")
        + line(label + "=" + value(m.value))
    )
