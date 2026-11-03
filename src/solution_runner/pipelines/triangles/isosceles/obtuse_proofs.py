"""Preserve the reviewed supplementary-angle methods and their order."""

import hashlib

import sympy as sp

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from .side_altitude_proofs import number, trig

_PARENTS = {
    "isosceles-triangle-27345-obtuse-sine-from-side-and-altitude": "5dc867c3f8708dd3d73e9e66ced209d0e1be7fae607362a8e864f6fa9283137b",
    "isosceles-triangle-27346-obtuse-cosine-from-side-and-altitude": "e31f4c572d964d696519ea652b91f160a4b141b83b0a4dffc4485b8c145125d6",
    "isosceles-triangle-27347-obtuse-tangent-from-side-and-altitude": "671f0f32ce9e764581b0872cf8e78e194e21444d4ca1d58bc4c18c56b45d58fe",
    "isosceles-triangle-27349-obtuse-cosine-from-side-and-projection": "8355a8b0e483a00da610ad560a24f88ae83e7a167003994f305c1dd6e71de346",
    "isosceles-triangle-27350-obtuse-tangent-from-side-and-projection": "770c33328a1e8a2c493c012d89faacc3e36e392cd82600c717334840d9d1a1ba",
    "isosceles-triangle-27351-obtuse-sine-from-altitude-and-projection": "4c59437a893931f87232ff982f7923b6dcc2667a271529b0cde89433b2478002",
    "isosceles-triangle-27352-obtuse-cosine-from-altitude-and-projection": "80e31292567ab9937c850c5409baf92fe81f1d63fedbf647d851772796788f0e",
    "isosceles-triangle-27353-obtuse-tangent-from-altitude-and-projection": "5cee4a09014527f348de9424cc6bf5d20b54fc3138da4136c6422103175c73af",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError("the complete obtuse parent methods must be reviewed")


def _length_rows(m):
    p, r = m.vertex, m.apex
    side, height, projection = p + r, p + "H", r + "H"
    s, h, d = number(m.side), number(m.height), number(m.projection)
    if m.given_kind == "side_height" and m.function != "sin":
        return (
            f"<p>Найдем катет {projection} по теореме Пифагора:</p>"
            + line(projection + r"=\sqrt{" + side + "^2-" + height + "^2}")
            + line(projection + r"=\sqrt{(" + s + ")^2-(" + h + ")^2}")
            + line(projection + "=" + d)
        )
    if m.given_kind == "side_projection" and m.function != "cos":
        return (
            f"<p>Найдем катет {height} по теореме Пифагора:</p>"
            + line(height + r"=\sqrt{" + side + "^2-" + projection + "^2}")
            + line(height + r"=\sqrt{(" + s + ")^2-(" + d + ")^2}")
            + line(height + "=" + h)
        )
    if m.given_kind == "height_projection" and m.function != "tg":
        return (
            f"<p>Найдем гипотенузу {side} по теореме Пифагора:</p>"
            + line(side + r"=\sqrt{" + height + "^2+" + projection + "^2}")
            + line(side + r"=\sqrt{(" + h + ")^2+(" + d + ")^2}")
            + line(side + "=" + s)
        )
    return ""


def _direct(m):
    p, r, q = m.vertex, m.apex, m.other_base_vertex
    alpha = p + r + "H"
    name = trig(m.function, m.requested)
    sign = "" if m.function == "sin" else "-"
    numerator = p + "H" if m.function != "cos" else r + "H"
    denominator = p + r if m.function != "tg" else r + "H"
    top = number(m.height if m.function != "cos" else m.projection)
    bottom = number(m.side if m.function != "tg" else m.projection)
    return (
        f"<p>В равнобедренном тупоугольном треугольнике ABC тупой угол находится при вершине {r}. Основание высоты {p}H лежит на продолжении стороны {q + r} за точку {r}. Углы {p + r + q} и {alpha} смежные:</p>"
        + line(r"\angle " + p + r + q + r"+\angle " + alpha + r"=180^{\circ}")
        + _length_rows(m)
        + "<p>Используем формулу приведения и определение тригонометрической функции в прямоугольном треугольнике:</p>"
        + line(name + "=" + sign + trig(m.function, alpha))
        + line(name + "=" + sign + r"\frac{" + numerator + "}{" + denominator + "}")
        + line(name + "=" + sign + r"\frac{" + top + "}{" + bottom + "}")
        + line(name + "=" + number(m.answer))
    )


def _angle_method(m):
    p, r, q = m.vertex, m.apex, m.other_base_vertex
    alpha = p + r + "H"
    name = trig("sin", m.requested)
    if sp.simplify(m.height / m.side - sp.Rational(1, 2)) == 0:
        return (
            f"<p>В прямоугольном треугольнике {alpha} катет {p}H равен половине гипотенузы {p + r}, поэтому лежит напротив угла в 30°:</p>"
            + line(p + "H" + "=" + number(m.height))
            + line(p + r + "=2" + p + "H" + "=" + number(m.side))
            + line(r"\angle " + alpha + r"=30^{\circ}")
            + line(r"\angle " + p + r + q + r"=180^{\circ}-30^{\circ}=150^{\circ}")
            + line(name + r"=\sin 150^{\circ}=\sin 30^{\circ}=\frac{1}{2}")
        )
    return (
        f"<p>Катет {p}H здесь не равен половине гипотенузы {p + r}, поэтому этот угол нельзя считать равным 30°. Найдем синус острого угла {alpha}, смежного с искомым:</p>"
        + line(trig("sin", alpha) + r"=\frac{" + p + "H" + "}{" + p + r + "}")
        + line(
            trig("sin", alpha)
            + r"=\frac{"
            + number(m.height)
            + "}{"
            + number(m.side)
            + "}="
            + number(m.answer)
        )
        + line(r"\angle " + p + r + q + r"=180^{\circ}-\angle " + alpha)
        + "<p>Синусы смежных углов равны:</p>"
        + line(name + "=" + trig("sin", alpha) + "=" + number(m.answer))
    )


def _area_method(m):
    p, r, q = m.vertex, m.apex, m.other_base_vertex
    name = trig("sin", m.requested)
    return (
        "<p>Выразим площадь треугольника двумя способами: через две стороны и угол между ними, затем через сторону и проведенную к ее прямой высоту:</p>"
        + line(r"S=\frac{1}{2}" + p + r + r"\cdot " + q + r + name)
        + line(r"S=\frac{1}{2}\cdot(" + number(m.side) + r")^2" + name)
        + line(r"S=\frac{1}{2}" + p + "H" + r"\cdot " + q + r)
        + line(
            r"S=\frac{1}{2}\cdot("
            + number(m.height)
            + r")\cdot("
            + number(m.side)
            + ")="
            + number(m.height * m.side / 2)
        )
        + "<p>Приравниваем выражения площади и делим на положительный коэффициент:</p>"
        + line(number(m.side**2 / 2) + name + "=" + number(m.height * m.side / 2))
        + line(
            name
            + r"=\frac{"
            + number(m.height * m.side / 2)
            + "}{"
            + number(m.side**2 / 2)
            + "}="
            + number(m.height / m.side)
        )
    )


def render(m, rule):
    m.require_rule(rule)
    html = solution_section("Решение", _direct(m))
    if (m.given_kind, m.function) == ("side_height", "sin"):
        html += solution_section("Приведём другое решение", _angle_method(m))
        html += solution_section("Приведём ещё одно решение", _area_method(m))
    return html
