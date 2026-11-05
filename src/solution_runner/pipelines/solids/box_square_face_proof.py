"""Keep the parent's height, square-face diagonal, area and volume calculation."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def render(m, picture):
    d, angle = m.given
    height = m.edges[2]
    diagonal = sp.simplify(m.edges[0] * sp.sqrt(2))
    area = sp.simplify(diagonal**2 / 2)
    theta = value(angle) + r"^{\circ}"
    sine = sp.sin(angle * sp.pi / 180)
    cosine = sp.cos(angle * sp.pi / 180)
    same = (
        " При угле 45° этот прямоугольный треугольник равнобедренный."
        if angle == 45
        else ""
    )
    return (
        "<p>"
        + picture
        + "Диагональ параллелепипеда, её проекция на квадратную грань и ребро, перпендикулярное этой грани, образуют прямоугольный треугольник."
        + same
        + " Найдём высоту h — ребро, лежащее напротив заданного угла:</p>"
        + line(r"h=d\sin " + theta)
        + line("h=" + bracket(d) + r"\cdot" + bracket(sine) + "=" + value(height))
        + "<p>Проекция пространственной диагонали на квадратную грань является диагональю этой грани. Найдём её длину q:</p>"
        + line(r"q=d\cos " + theta)
        + line("q=" + bracket(d) + r"\cdot" + bracket(cosine) + "=" + value(diagonal))
        + "<p>Площадь квадрата равна половине произведения его равных диагоналей:</p>"
        + line(r"S=\frac{q^2}{2}")
        + line(r"S=\frac{" + bracket(diagonal) + "^2}{2}=" + value(area))
        + "<p>Тогда объём параллелепипеда равен произведению площади выбранной грани и перпендикулярного ей ребра:</p>"
        + line(r"V=Sh")
        + line(
            "V=" + bracket(area) + r"\cdot" + bracket(height) + "=" + value(m.answer)
        )
    )
