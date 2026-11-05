"""Prove the actual rectangle and use half the vertical edge in Pythagoras."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import box_coordinates as c
from .distance_proofs import given, html_name


def render(m, picture):
    a, b, d, e = m.vertices
    other = dict(m.extra_points)["K_1"]
    bottom = next(n for n, p in c.VERTICES.items() if p == (*other[:2], 0))
    top = bottom + "_1"
    r = m.right
    horizontal, amount = given(m, a + r)
    vertical, height = next((n, v) for n, v in m.given if c.axes(n) == (2,))
    side, edge = given(m, m.edge)
    half = sp.simplify(height / 2)
    square = sp.simplify(amount**2 + half**2)
    hyp = m.length(a, e)
    return (
        "<p>"
        + picture
        + "Обозначим через "
        + html_name("K_1")
        + " точку пересечения секущей плоскости с ребром "
        + html_name(bottom + top)
        + ". Сечение пересекает параллельные боковые грани по параллельным отрезкам. Параллельные рёбра равны, поэтому "
        + html_name("K_1")
        + " также является серединой ребра. Четырёхугольник "
        + html_name("".join(m.vertices))
        + " — параллелограмм. Его сторона "
        + html_name(m.edge)
        + " перпендикулярна боковым граням, содержащим стороны "
        + html_name(a + e)
        + " и "
        + html_name(b + d)
        + ", поэтому этот параллелограмм — прямоугольник.</p>"
        + "<p>Найдём сторону "
        + html_name(m.diagonal)
        + " из прямоугольного треугольника "
        + html_name(a + r + e)
        + ". Используем равенство параллельных рёбер и определение середины:</p>"
        + line(
            r
            + e
            + r"=\frac{"
            + vertical
            + "}{2}=\\frac{"
            + value(height)
            + "}{2}="
            + value(half)
        )
        + line(
            a
            + r
            + ("=" + horizontal if a + r != horizontal else "")
            + "="
            + value(amount)
        )
        + line(m.diagonal + "^2=" + a + r + "^2+" + r + e + "^2")
        + line(
            m.diagonal
            + "^2="
            + bracket(amount)
            + "^2+"
            + bracket(half)
            + "^2="
            + value(square)
        )
        + line(m.diagonal + r"=\sqrt{" + value(square) + "}=" + value(hyp))
        + "<p>Тогда площадь прямоугольного сечения равна произведению его соседних сторон:</p>"
        + line(m.edge + ("=" + side if m.edge != side else "") + "=" + value(edge))
        + line("S=" + m.edge + r"\cdot " + m.diagonal)
        + line("S=" + bracket(edge) + r"\cdot" + bracket(hyp) + "=" + value(m.answer))
    )
