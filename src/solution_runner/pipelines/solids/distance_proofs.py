"""Keep the parent's face-then-space Pythagoras method with actual segment names."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import box_coordinates as c
from .box_distance_geometry import scene


def label(segment):
    return "".join(sorted(c.endpoints(segment)))


def length(m, segment):
    return sp.sqrt(c.squared_length(segment, m.squares))


def given(m, segment):
    mask = c.axes(segment)
    return next((s, v) for s, v in m.given if c.axes(s) == mask)


def _face(m, segment, legs, *, root):
    f = label(segment)
    a, b = (label(v) for v in legs)
    ga, va = given(m, legs[0])
    gb, vb = given(m, legs[1])
    square = c.squared_length(segment, m.squares)
    rows = line(f + "^2=" + a + "^2+" + b + "^2")
    if (label(ga), label(gb)) != (a, b):
        rows += line(f + "^2=" + label(ga) + "^2+" + label(gb) + "^2")
    rows += line(f + "^2=" + bracket(va) + "^2+" + bracket(vb) + "^2")
    rows += line(
        f + "^2=" + value(va * va) + "+" + value(vb * vb) + "=" + value(square)
    )
    if root:
        rows += line(f + r"=\sqrt{" + value(square) + "}=" + value(sp.sqrt(square)))
    return rows


def html_name(name):
    return "<i>" + name.replace("_1", "<sub>1</sub>") + "</i>"


def _inverse(m, picture, s):
    hyp, face, leg = (label(s[k]) for k in ("hyp", "face", "leg"))
    h, hd = next((name, v) for name, v in m.given if len(c.axes(name)) == 3)
    square = c.squared_length(m.requested, m.squares)
    fs = c.squared_length(s["face"], m.squares)
    a, b = c.endpoints(s["hyp"])
    triangle = s["right"] + b + a
    equality = (
        "Пространственные диагонали прямоугольного параллелепипеда равны. "
        if hyp != label(h)
        else ""
    )
    result = (
        "<p>"
        + picture
        + "Найдём диагональ "
        + html_name(face)
        + " соответствующей грани по теореме Пифагора. Используем равенство параллельных рёбер:</p>"
        + _face(m, s["face"], s["face_legs"], root=True)
        + "<p>"
        + equality
        + "В прямоугольном треугольнике "
        + html_name(triangle)
        + " найдём неизвестное ребро:</p>"
        + line(hyp + ("=" + label(h) if hyp != label(h) else "") + "=" + value(hd))
        + line(leg + "^2=" + hyp + "^2-" + face + "^2")
        + line(
            leg
            + "^2="
            + bracket(hd)
            + r"^2-\left("
            + value(sp.sqrt(fs))
            + r"\right)^2="
            + value(square)
        )
        + line(leg + r"=\sqrt{" + value(square) + "}=" + value(m.answer))
    )
    target = label(m.requested)
    return result + (
        line(target + "=" + leg + "=" + value(m.answer)) if target != leg else ""
    )


def _face_distance(m, picture, s):
    a, b = c.endpoints(s["hyp"])
    right = s["right"]
    fourth = next(
        n
        for n, p in c.VERTICES.items()
        if p
        == tuple(
            x + y - z
            for x, y, z in zip(c.VERTICES[a], c.VERTICES[b], c.VERTICES[right])
        )
    )
    rectangle = a + right + b + fourth
    return (
        "<p>"
        + picture
        + "В прямоугольнике "
        + html_name(rectangle)
        + " искомый отрезок "
        + html_name(label(s["hyp"]))
        + " является диагональю. Применим теорему Пифагора и равенство параллельных рёбер:</p>"
        + _face(m, s["hyp"], s["legs"], root=m.mode != "distance_squared")
    )


def _space_distance(m, picture, s):
    hyp, face, leg = (label(s[k]) for k in ("hyp", "face", "leg"))
    lv = length(m, s["leg"])
    fs = c.squared_length(s["face"], m.squares)
    total = c.squared_length(s["hyp"], m.squares)
    a, b = c.endpoints(s["hyp"])
    triangle = s["right"] + b + a
    theorem = line(hyp + "^2=" + leg + "^2+" + face + "^2")
    intro = (
        "Найдём диагональ "
        + html_name(face)
        + " грани ABCD по теореме Пифагора. Параллельные рёбра прямоугольного параллелепипеда равны:</p>"
    )
    if m.mode == "distance_squared":
        body = (
            "<p>"
            + picture
            + "В прямоугольном треугольнике "
            + html_name(triangle)
            + " пространственная диагональ является гипотенузой:</p>"
            + theorem
            + "<p>"
            + intro
        )
    else:
        body = "<p>" + picture + intro
    body += _face(m, s["face"], s["face_legs"], root=m.mode != "distance_squared")
    if m.mode != "distance_squared":
        body += (
            "<p>Теперь рассмотрим прямоугольный треугольник "
            + html_name(triangle)
            + " с пространственной диагональю:</p>"
            + theorem
        )
    actual, v = given(m, s["leg"])
    if label(actual) != leg:
        body += line(leg + "=" + label(actual) + "=" + value(v))
    body += line(hyp + "^2=" + bracket(lv) + "^2+" + value(fs) + "=" + value(total))
    if m.mode != "distance_squared":
        body += line(hyp + r"=\sqrt{" + value(total) + "}=" + value(m.answer))
    return body


def render(m, picture):
    s = scene(m)
    if m.mode == "edge":
        return _inverse(m, picture, s)
    if "legs" in s:
        return _face_distance(m, picture, s)
    if "face" in s:
        return _space_distance(m, picture, s)
    target = label(m.requested)
    name, v = given(m, m.requested)
    formula = (
        target + "^2=" + label(name) + "^2=" + value(v * v)
        if m.mode == "distance_squared"
        else target
        + ("=" + label(name) if target != label(name) else "")
        + "="
        + value(v)
    )
    return (
        "<p>"
        + picture
        + "Искомое ребро равно параллельному ему данному ребру:</p>"
        + line(formula)
    )
