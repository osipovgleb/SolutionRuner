"""Use parallel lines, one face Pythagoras calculation and the sine ratio."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import value
from . import box_coordinates as c
from .distance_proofs import _face, html_name, label


def render(m, picture):
    a, b = c.endpoints(m.diagonal)
    right = m.right
    adjacent, opposite = right + b, a + right
    hyp = label(m.diagonal)
    parallel = (
        ""
        if set(c.endpoints(m.edge)) == set(c.endpoints(adjacent))
        else "Прямые "
        + html_name(label(m.edge))
        + " и "
        + html_name(label(adjacent))
        + " параллельны. "
    )
    angle = a + b + right
    length = sp.sqrt(c.squared_length(m.diagonal, m.squares))
    side = sp.sqrt(c.squared_length(opposite, m.squares))
    return (
        "<p>"
        + picture
        + parallel
        + "Искомый синус равен синусу острого угла "
        + html_name(angle)
        + ". Найдём гипотенузу прямоугольного треугольника "
        + html_name(a + b + right)
        + " по теореме Пифагора. Используем равенство параллельных рёбер:</p>"
        + _face(m, m.diagonal, (adjacent, opposite), root=True)
        + "<p>Синус острого угла равен отношению противолежащего катета к гипотенузе:</p>"
        + line(r"\sin " + angle + r"=\frac{" + label(opposite) + "}{" + hyp + "}")
        + line(
            r"\sin "
            + angle
            + r"=\frac{"
            + value(side)
            + "}{"
            + value(length)
            + "}="
            + value(m.answer)
        )
    )
