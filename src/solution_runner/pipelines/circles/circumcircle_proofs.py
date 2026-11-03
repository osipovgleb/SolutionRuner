"""Preserve sine, direct-formula and median methods with their original layout."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section
from . import (
    circumcircle_height_proof,
    circumcircle_polygon_proof,
    circumcircle_quantity_proofs,
    circumcircle_trapezoid_proofs,
)

INTRO = "<p>Треугольник ABC правильный, значит, все его углы равны 60°. По теореме синусов:</p>"


def _radius_side(m):
    side = m.given[0]
    height = side * sp.sqrt(3) / 2
    first = (
        INTRO
        + line(r"R=\frac{AC}{2\sin B}")
        + line(r"R=\frac{" + value(side) + r"}{2\sin60^{\circ}}")
        + line(r"R=\frac{" + value(side) + r"}{2}\cdot\frac{2}{\sqrt{3}}")
        + line("R=" + value(m.answer))
    )
    second = (
        "<p>Радиус R описанной окружности и сторона a правильного треугольника связаны соотношением:</p>"
        + line(r"R=\frac{a\sqrt{3}}{3}")
        + line(r"R=\frac{" + bracket(side) + r"\cdot\sqrt{3}}{3}=" + value(m.answer))
        + "<p><b>Приведем еще одно решение.</b></p><p>Центр описанной окружности правильного треугольника находится в точке пересечения его медиан, биссектрис и высот. Найдём высоту:</p>"
        + line(r"h=a\sin60^{\circ}")
        + line("h=" + bracket(side) + r"\cdot\frac{\sqrt{3}}{2}=" + value(height))
        + "<p>Медианы точкой пересечения делятся в отношении 2:1, считая от вершины:</p>"
        + line(r"R=\frac{2}{3}h")
        + line(r"R=\frac{2}{3}\cdot " + bracket(height) + "=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Приведем другое решение.", second
    )


def _side_radius(m):
    radius = m.given[0]
    return solution_section(
        "Решение",
        INTRO
        + line(r"CB=2R\sin A")
        + line(r"\sin A=\sin60^{\circ}=\frac{\sqrt{3}}{2}")
        + line(r"CB=2\cdot " + bracket(radius) + r"\cdot\frac{\sqrt{3}}{2}")
        + line("CB=" + value(m.answer)),
    )


def _radius_height(m):
    height = m.given[0]
    first = (
        INTRO
        + line(r"R=\frac{AC}{2\sin B}")
        + line(r"AC=\frac{CH}{\sin A}")
        + line(r"R=\frac{CH}{2\sin A\cdot\sin B}")
        + line(r"R=\frac{" + value(height) + r"}{2\sin^2 60^{\circ}}")
        + line(r"R=\frac{" + value(height) + r"}{2}\cdot\frac{4}{3}=" + value(m.answer))
    )
    second = (
        "<p>В правильном треугольнике радиус описанной окружности равен двум третьим высоты. Поэтому:</p>"
        + line(r"R=\frac{2}{3}h")
        + line(r"R=\frac{2}{3}\cdot " + bracket(height))
        + line("R=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Приведём другое решение.", second
    )


def _height_radius(m):
    radius = m.given[0]
    first = (
        INTRO
        + line(r"CH=AC\sin A")
        + line(r"AC=2R\sin B")
        + line(r"CH=2R\sin B\sin A=2R\sin^2 60^{\circ}")
        + line(r"CH=2\cdot " + bracket(radius) + r"\cdot\frac{3}{4}")
        + line("CH=" + value(m.answer))
    )
    second = (
        "<p>Центр описанной окружности лежит в точке пересечения серединных перпендикуляров. В правильном треугольнике в этой же точке пересекаются медианы, биссектрисы и высоты. Медианы делятся в отношении 2:1 от вершины, поэтому OC вдвое больше OH:</p>"
        + line("OC=2OH")
        + line(r"OH=\frac{OC}{2}")
        + line(r"OH=\frac{" + value(radius) + "}{2}=" + value(radius / 2))
        + "<p>Высота CH состоит из радиуса CO и отрезка OH:</p>"
        + line("CH=CO+OH")
        + line("CH=" + value(radius) + "+" + value(radius / 2) + "=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Приведем другое решение.", second
    )


def render(m, pictures):
    if m.mode == "trapezoid_height":
        return circumcircle_height_proof.render(m, pictures)
    if m.mode in circumcircle_trapezoid_proofs.MODES:
        return circumcircle_trapezoid_proofs.render(m, pictures)
    if m.mode == "polygon_vertices":
        return circumcircle_polygon_proof.render(m, pictures)
    if m.mode in circumcircle_quantity_proofs.MODES:
        return circumcircle_quantity_proofs.render(m, pictures)
    return {
        "radius_side": _radius_side,
        "side_radius": _side_radius,
        "radius_height": _radius_height,
        "height_radius": _height_radius,
    }[m.mode](m)
