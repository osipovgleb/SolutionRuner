"""Preserve the equilateral sine arguments and both base/height angle methods."""

import hashlib

import sympy as sp

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from .side_altitude_proofs import number

_PARENTS = {
    "isosceles-triangle-27792-equilateral-height-from-side": "c54f8342ba0d9d103e50cac9e4e9f43a82bd6e1084f53a5f7aa968eacba96c86",
    "isosceles-triangle-27793-equilateral-side-from-height": "0a15f31f505a07255e0d7a5a99b258198ef3bf7f83b39b4d67268496922847e1",
    "isosceles-triangle-27794-vertex-angle-from-base-altitude": "189db3dcb4f7e981c93e2e9beb9d11e9e5f87bc3f98e9c7e7908f7e0b2572efd",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError(
            "the complete base-height parent methods must be reviewed"
        )


def _pair(m):
    p = m.base_vertices[0]
    side = m.side_segment
    height = m.height_segment
    trig = r"\sin\angle " + p
    body = "<p>Треугольник ABC — равносторонний, значит, все углы в нем равны 60°. Используем определение синуса в прямоугольном треугольнике:</p>"
    if m.mode == "side_to_height":
        body += line(height + "=" + side + trig)
        body += line(height + "=(" + m.first_raw + r")\sin 60^{\circ}")
    else:
        body += line(side + r"=\frac{" + height + "}{" + trig + "}")
        body += line(side + r"=\frac{" + m.first_raw + r"}{\sin 60^{\circ}}")
    body += line(r"\sin 60^{\circ}=\frac{\sqrt{3}}{2}")
    body += "<p>Подставим известное значение синуса и упростим:</p>"
    if m.mode == "side_to_height":
        body += line(height + "=(" + m.first_raw + r")\cdot\frac{\sqrt{3}}{2}")
        body += line(height + r"=\frac{" + number(m.side * sp.sqrt(3)) + "}{2}")
        return body + line(height + "=" + number(m.answer))
    body += line(side + "=(" + m.first_raw + r")\cdot\frac{2}{\sqrt{3}}")
    body += line(side + r"=\frac{" + number(2 * m.height) + r"}{\sqrt{3}}")
    return body + line(side + "=" + number(m.answer))


def _half_base(m):
    p, q = m.base_vertices
    return (
        "<p>Высота в равнобедренном треугольнике является медианой и делит основание пополам:</p>"
        + line(p + "H=" + q + r"H=\frac{" + m.base_segment + "}{2}")
        + line(p + r"H=\frac{" + m.first_raw + "}{2}=" + number(m.base / 2))
    )


def _pythagoras(m):
    p = m.base_vertices[0]
    side = m.side_segment
    half = p + "H"
    height = m.height_segment
    alpha = p + m.vertex + "H"
    body = (
        _half_base(m)
        + f"<p>В прямоугольном треугольнике {p + 'H' + m.vertex} по теореме Пифагора получаем:</p>"
    )
    body += line(side + r"=\sqrt{" + half + "^2+" + height + "^2}")
    body += line(
        side
        + r"=\sqrt{("
        + number(m.base / 2)
        + ")^2+("
        + m.second_raw
        + ")^2}="
        + number(m.side)
    )
    if sp.simplify(m.base - m.side) == 0:
        body += line(half + r"=\frac{" + side + "}{2}")
        body += f"<p>Угол {alpha}, лежащий против катета, равного половине гипотенузы, равен 30°:</p>"
        body += line(r"\angle " + alpha + r"=30^{\circ}")
    else:
        body += "<p>По отношению противолежащего катета к гипотенузе находим острый угол:</p>"
        body += line(
            r"\sin\angle "
            + alpha
            + r"=\frac{"
            + half
            + "}{"
            + side
            + "}="
            + number(m.base / (2 * m.side))
        )
        body += line(r"\angle " + alpha + "=" + number(m.apex_angle / 2) + r"^{\circ}")
    body += "<p>Высота к основанию является также биссектрисой. Искомый угол вдвое больше:</p>"
    return body + line(
        r"\angle "
        + m.vertex
        + r"=2\angle "
        + alpha
        + r"=2\cdot"
        + number(m.apex_angle / 2)
        + r"^{\circ}="
        + number(m.apex_angle)
        + r"^{\circ}"
    )


def _tangent(m):
    q = m.base_vertices[1]
    beta = m.vertex + q + "H"
    value = (180 - m.apex_angle) / 2
    body = (
        _half_base(m)
        + f"<p>В прямоугольном треугольнике {m.vertex + q + 'H'} находим:</p>"
    )
    body += line(r"\tg\angle " + beta + r"=\frac{" + m.height_segment + "}{" + q + "H}")
    body += line(
        r"\tg\angle "
        + beta
        + r"=\frac{"
        + m.second_raw
        + "}{"
        + number(m.base / 2)
        + "}="
        + number(2 * m.height / m.base)
    )
    body += line(r"\angle " + beta + "=" + number(value) + r"^{\circ}")
    if value == 60:
        body += "<p>Равнобедренный треугольник с углом 60° — равносторонний. Следовательно, все его углы равны 60°:</p>"
        return body + line(r"\angle " + m.vertex + r"=60^{\circ}")
    body += "<p>Углы при основании равны. По сумме углов треугольника:</p>"
    return body + line(
        r"\angle "
        + m.vertex
        + r"=180^{\circ}-2\cdot"
        + number(value)
        + r"^{\circ}="
        + number(m.apex_angle)
        + r"^{\circ}"
    )


def render(m, rule):
    m.require_rule(rule)
    if m.mode != "base_height_to_angle":
        return solution_section("Решение", _pair(m))
    return solution_section("Решение", _pythagoras(m)) + solution_section(
        "Приведем другое решение", _tangent(m)
    )
