"""Render the reviewed sine-area and base-altitude methods in separate steps."""

import hashlib

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from .side_altitude_proofs import number

_PARENTS = {
    "isosceles-triangle-27589-area-from-side-and-30-degree-vertex-angle": "764f865bf5a9cbb0e523bc9cc1d9e6a42b9595c670a8feaac06b987c3531acd3",
    "isosceles-triangle-27590-area-from-side-and-150-degree-vertex-angle": "55512c893484d74ebb1826cd39d9ce98d65eedc15ef96926fb8105615dc63c1e",
    "isosceles-triangle-27619-area-from-side-and-base": "f46e3c85cd8edeaea87df2526475b63d798ecf024054adab839db45832ae4127",
    "isosceles-triangle-27620-side-from-area-and-30-degree-vertex-angle": "edc58294f84c34185e8537d54436da351b5fc3689c68d922b9621887d4dc9cc0",
    "isosceles-triangle-27621-side-from-area-and-150-degree-vertex-angle": "92b9537f9d12b2f709cebac138082c50f89ec8f478f5c548dfeeaa649442bc00",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError("the full parent area method must be reviewed")


def _sine(m):
    angle = str(m.angle) + r"^{\circ}"
    sine = r"\sin " + angle
    body = "<p>Обозначим боковую сторону через a. Площадь треугольника равна половине произведения двух сторон на синус угла между ними:</p>"
    body += line(r"S=\frac{1}{2}a^2" + sine)
    if m.angle == 150:
        body += "<p>Синусы смежных углов равны:</p>"
        body += line(
            r"\sin 150^{\circ}=\sin(180^{\circ}-30^{\circ})=\sin 30^{\circ}=\frac{1}{2}"
        )
    else:
        body += line(sine + r"=\frac{1}{2}")
    if m.given_kind == "side_angle":
        body += line(r"S=\frac{1}{2}\cdot(" + m.first_raw + r")^2\cdot\frac{1}{2}")
        body += line(r"S=\frac{(" + m.first_raw + r")^2}{4}")
        body += line(r"S=\frac{" + number(m.side**2) + "}{4}")
        return body + line("S=" + number(m.answer))
    body += line(r"S=\frac{a^2}{4}")
    body += "<p>Подставим заданную площадь и найдем положительную длину стороны:</p>"
    body += line(r"\frac{a^2}{4}=" + m.first_raw)
    body += line(r"a^2=4\cdot(" + m.first_raw + ")=" + number(4 * m.area))
    body += line(r"a=\sqrt{" + number(4 * m.area) + "}=" + number(m.answer))
    return body


def _base(m):
    return (
        "<p>Обозначим боковую сторону через a, основание через b, высоту к основанию через h. Высота равнобедренного треугольника делит его на два равных прямоугольных треугольника, а основание — пополам. Найдем высоту по теореме Пифагора:</p>"
        + line(r"h^2=a^2-\left(\frac{b}{2}\right)^2")
        + line(
            r"h^2=("
            + m.first_raw
            + r")^2-\left(\frac{"
            + m.second_raw
            + r"}{2}\right)^2"
        )
        + line(
            r"h^2="
            + number(m.side**2)
            + "-"
            + number(m.base**2 / 4)
            + "="
            + number(m.height**2)
        )
        + line(r"h=\sqrt{" + number(m.height**2) + "}=" + number(m.height))
        + "<p>Площадь равна половине произведения основания на высоту:</p>"
        + line(r"S=\frac{1}{2}bh")
        + line(
            r"S=\frac{1}{2}\cdot(" + m.second_raw + r")\cdot(" + number(m.height) + ")"
        )
        + line("S=" + number(m.answer))
    )


def render(model, rule):
    model.require_rule(rule)
    return solution_section(
        "Решение", _base(model) if model.given_kind == "side_base" else _sine(model)
    )
