"""Preserve the seven parent angle methods with explicit supplementary steps."""

import hashlib
from dataclasses import replace

from ...core.errors import ContentPlanError
from ...probability.common import line
from ..right.altitude_methods import solution_section
from .side_altitude_proofs import number

_PARENTS = {
    "isosceles-triangle-27760-vertex-angle-from-altitude-angle": "807cceb27eef28eff280b816d2eaa1b3347583f24e14ac40869d66c3bba5df9b",
    "isosceles-triangle-27744-vertex-angle-from-base-angle": "b096071cbb801dc1b24149b5ec08f7d7cbb4f57fca8ef1af2512611c3dbe87e5",
    "isosceles-triangle-27745-base-angle-from-vertex-angle": "894733d3fc6d4709b2445bb55fab9a062836089f637e12c8a41d2799def27c1c",
    "isosceles-triangle-27746-exterior-angle-from-vertex-angle": "16d78601a2d7ea852a66b014869c60cb3d0560a796416d87f21ede48986ff411",
    "isosceles-triangle-27747-vertex-angle-from-exterior-base-angle": "dd26294147e5e4bc77676ed5d3ec23b5dbab8edc67b6924360422764dd06a689",
    "isosceles-triangle-27748-base-angle-from-exterior-vertex-angle": "17093e2b7972611f7e9efbdc24ccf9e394522b14f080408b5bf5f27f1c97ab8b",
    "isosceles-triangle-27750-smaller-angle-from-larger-angle": "b378a28231f4246bdafeeff7d8bfb344f2088a580217dfa5deab23d3e4a1c71a",
    "isosceles-triangle-27754-smaller-angle-from-angle-difference": "4e1d80d9a0c008614acf1b78ab482996372886b0eacd32ea5d820780036aa30f",
}


def review_parent(html, rule):
    if not isinstance(html, str) or hashlib.sha256(
        html.encode()
    ).hexdigest() != _PARENTS.get(rule):
        raise ContentPlanError("the full parent angle method must be reviewed")


def degree(value):
    return number(value) + r"^{\circ}"


def angle(vertex):
    return r"\angle " + vertex


def _base(m):
    p, q = m.base_vertices
    c = m.apex
    target = m.requested if m.requested_kind in {"base", "smaller"} else p
    return (
        f"<p>Углы {p} и {q} при основании равнобедренного треугольника равны. Найдем каждый из них по сумме углов треугольника:</p>"
        + line(angle(p) + "=" + angle(q))
        + line(angle(target) + r"=\frac{180^{\circ}-" + angle(c) + "}{2}")
        + line(angle(target) + r"=\frac{180^{\circ}-" + degree(m.apex_angle) + "}{2}")
        + line(
            angle(target)
            + r"=\frac{"
            + degree(180 - m.apex_angle)
            + "}{2}="
            + degree(m.base_angle)
        )
    )


def _vertex(m):
    p, q = m.base_vertices
    c = m.apex
    return (
        f"<p>Углы {p} и {q} при основании равнобедренного треугольника равны:</p>"
        + line(angle(p) + "=" + angle(q) + "=" + degree(m.base_angle))
        + "<p>Сумма углов треугольника равна 180°:</p>"
        + line(angle(c) + r"=180^{\circ}-" + angle(p) + "-" + angle(q))
        + line(angle(c) + r"=180^{\circ}-2" + angle(m.given_vertex))
        + line(angle(c) + r"=180^{\circ}-2\cdot" + degree(m.base_angle))
        + line(
            angle(c)
            + r"=180^{\circ}-"
            + degree(2 * m.base_angle)
            + "="
            + degree(m.apex_angle)
        )
    )


def _external(m):
    vertex = m.given_vertex
    interior = m.apex_angle if m.given_kind == "external_vertex" else m.base_angle
    body = (
        f"<p>Внутренний угол {vertex} и данный внешний угол смежные:</p>"
        + line(angle(vertex) + r"=180^{\circ}-" + degree(m.given_value))
        + line(angle(vertex) + "=" + degree(interior))
    )
    return body + (_base(m) if m.given_kind == "external_vertex" else _vertex(m))


def _difference(m):
    d = number(m.given_value)
    x = number(m.answer)
    return (
        "<p>Углы при основании равнобедренного треугольника острые. При данной разности больший угол не может быть углом при основании. Пусть меньший угол равен x°, тогда угол при вершине равен (x + "
        + d
        + ")°. Два меньших угла при основании равны:</p>"
        + line("2x+(x+" + d + ")=180")
        + line("3x+" + d + "=180")
        + line("3x=180-" + d + "=" + number(180 - m.given_value))
        + "<p>Разделим обе части равенства на 3:</p>"
        + line(r"x=\frac{" + number(180 - m.given_value) + "}{3}=" + x)
    )


def _altitude(m):
    p, q = m.altitude_vertex, m.other_base_vertex
    body = (
        f"<p>Так как {p}D — высота, треугольник {p}{q}D прямоугольный. Найдем угол при основании:</p>"
        + line(angle(q) + r"=90^{\circ}-" + angle(m.given_vertex))
        + line(angle(q) + r"=90^{\circ}-" + degree(m.given_value))
        + line(angle(q) + "=" + degree(m.base_angle))
    )
    return body + _vertex(replace(m, given_vertex=q))


def render(m, rule):
    m.require_rule(rule)
    if m.given_kind == "altitude":
        body = _altitude(m)
    elif m.given_kind == "difference":
        body = _difference(m)
    elif m.given_kind.startswith("external_"):
        body = _external(m)
    elif m.given_kind == "base":
        body = _vertex(m)
    else:
        intro = (
            "<p>Данный больший угол неострый, а углы при основании равнобедренного треугольника острые. Поэтому данный угол находится при вершине.</p>"
            if m.given_kind == "larger"
            else ""
        )
        body = intro + _base(m)
        if m.requested_kind == "external_base":
            body += (
                "<p>Искомый внешний угол смежный с внутренним углом при основании:</p>"
            )
            body += line(angle(m.requested) + r"=180^{\circ}-" + angle(m.requested[1]))
            body += line(
                angle(m.requested)
                + r"=180^{\circ}-"
                + degree(m.base_angle)
                + "="
                + degree(m.answer)
            )
    return solution_section("Решение", body)
