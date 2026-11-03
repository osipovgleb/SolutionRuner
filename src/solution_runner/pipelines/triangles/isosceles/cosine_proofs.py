"""Preserve the cosine-law method and the inverse parent's sine-law alternative."""

import hashlib

import sympy as sp

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from .side_altitude_proofs import number

_PARENTS = {
    "isosceles-triangle-27799-side-from-base-vertex-angle": "abb811f5a449c1965f2da9f9058c1e9d003527c1e6252ee396feb1f9edd624f5",
    "isosceles-triangle-27800-base-from-side-vertex-angle": "200118faf55109d7fbd4d9a9e9a3b5018b0b2978a292684df0bc4390c69748a5",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError(
            "the complete cosine-law parent methods must be reviewed"
        )


def _law(m):
    a, c = m.equal_sides
    b = m.base_segment
    angle = r"\cos\angle " + m.apex
    return b + "^2=" + a + "^2+" + c + "^2-2" + a + r"\cdot " + c + angle


def _inverse(m):
    a = m.requested
    b = m.base_segment
    cosine = r"\cos\angle " + m.apex
    raw = m.length_raw
    return (
        "<p>Воспользуемся теоремой косинусов. Учитывая равенство боковых сторон, выразим искомую сторону:</p>"
        + line(_law(m))
        + line(b + "^2=2" + a + "^2(1-" + cosine + ")")
        + line(a + r"^2=\frac{" + b + r"^2}{2(1-" + cosine + ")}")
        + "<p>Подставим основание и косинус угла. Длина стороны положительна, поэтому выбираем положительный корень:</p>"
        + line(cosine + "=" + number(m.cosine))
        + line(a + r"=\sqrt{\frac{(" + raw + r")^2}{2(1-(" + number(m.cosine) + "))}}")
        + line(
            a + r"=\sqrt{\frac{" + number(m.base**2) + "}{" + number(m.factor) + "}}"
        )
        + line(a + "=" + number(m.answer))
    )


def _forward(m):
    b = m.base_segment
    raw = m.length_raw
    cos = number(m.cosine)
    sq = number(m.side**2)
    cross = sp.simplify(-2 * m.side**2 * m.cosine)
    signed = ("-" if cross.is_negative else "+") + number(abs(cross))
    return (
        "<p>Найдем косинус данного угла:</p>"
        + line(
            r"\cos\angle "
            + m.apex
            + r"=\cos "
            + number(m.apex_angle)
            + r"^{\circ}="
            + cos
        )
        + "<p>По теореме косинусов:</p>"
        + line(_law(m))
        + "<p>Подставим равные боковые стороны и выполним вычисления:</p>"
        + line(
            b
            + "^2=("
            + raw
            + ")^2+("
            + raw
            + r")^2-2\cdot("
            + raw
            + r")\cdot("
            + raw
            + r")\cdot("
            + cos
            + ")"
        )
        + line(b + "^2=" + sq + "+" + sq + r"-2\cdot(" + sq + r")\cdot(" + cos + ")")
        + line(b + "^2=" + sq + "+" + sq + signed + "=" + number(m.base**2))
        + "<p>Длина основания положительна:</p>"
        + line(b + r"=\sqrt{" + number(m.base**2) + "}=" + number(m.answer))
    )


def _sines(m):
    a = m.requested
    b = m.base_segment
    vertex = next(v for v in m.base_vertices if v not in a)
    beta = (180 - m.apex_angle) / 2
    sb = sp.simplify(sp.sin(sp.pi * beta / 180))
    sg = sp.simplify(sp.sin(sp.pi * m.apex_angle / 180))
    small = r"\sin\angle " + vertex
    large = r"\sin\angle " + m.apex
    return (
        "<p>Углы при основании равнобедренного треугольника равны. Найдем их и применим теорему синусов:</p>"
        + line(
            r"\angle "
            + vertex
            + r"=\frac{180^{\circ}-"
            + number(m.apex_angle)
            + r"^{\circ}}{2}="
            + number(beta)
            + r"^{\circ}"
        )
        + line(r"\frac{" + a + "}{" + small + r"}=\frac{" + b + "}{" + large + "}")
        + line(a + "=" + b + r"\cdot\frac{" + small + "}{" + large + "}")
        + line(
            a
            + "=("
            + m.length_raw
            + r")\cdot\frac{"
            + number(sb)
            + "}{"
            + number(sg)
            + "}"
        )
        + line(
            a
            + "=("
            + m.length_raw
            + r")\cdot("
            + number(sp.simplify(sb / sg))
            + ")="
            + number(m.answer)
        )
    )


def render(m, rule):
    m.require_rule(rule)
    html = solution_section(
        "Решение", _inverse(m) if m.requested_kind == "side" else _forward(m)
    )
    if m.requested_kind == "side":
        html += solution_section("Приведем другое решение", _sines(m))
    return html
