"""Adapt base-height, half-box and corner-complement proofs to actual vertices."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import box_coordinates as c
from .distance_proofs import given, html_name, label

BOX = r"V_{\mathrm{пар}}"
PYRAMID = r"V_{\mathrm{пир}}"
SOLID = r"V_{\mathrm{многогр}}"
CORNER = r"V_{\mathrm{угл}}"
AREA = r"S_{\mathrm{осн}}"
FACE = r"S_{\mathrm{грани}}"


def target(m):
    return SOLID if m.solid.kind == "prism" else PYRAMID


def _measure(m, segment, *, prefix=""):
    name, amount = given(m, segment)
    return line(
        prefix
        + label(segment)
        + ("=" + label(name) if label(segment) != label(name) else "")
        + "="
        + value(amount)
    )


def _box(m):
    if not m.given:
        return line(BOX + "=" + value(m.box_volume))
    names, values = zip(*(given(m, s) for s in ("AB", "AD", "AA_1")))
    result = line(BOX + r"=AB\cdot AD\cdot AA_1")
    if tuple(label(n) for n in names) != ("AB", "AD", "AA_1"):
        result += line(BOX + "=" + r"\cdot ".join(label(n) for n in names))
    return result + line(
        BOX
        + "="
        + r"\cdot ".join(bracket(v) for v in values)
        + "="
        + value(m.box_volume)
    )


def base_legs(solid):
    base = solid.base
    for p in base:
        others = [n for n in base if n != p and len(c.axes(p + n)) == 1]
        if len(others) == 2:
            return p + others[0], p + others[1]
    raise ValueError(
        "a recognized coordinate-face base must have two perpendicular edges"
    )


def _base_height(m):
    a, b = base_legs(m.solid)
    height = (
        m.solid.foot + m.solid.apex
        if m.solid.kind == "pyramid"
        else m.solid.base[0] + m.solid.upper[0]
    )
    va, vb = (given(m, s)[1] for s in (a, b))
    h = given(m, height)[1]
    factor = sp.Rational(1, 2) if len(m.solid.base) == 3 else sp.Integer(1)
    intro = (
        "Основание "
        + html_name("".join(m.solid.base))
        + (
            " — прямоугольный треугольник"
            if factor == sp.Rational(1, 2)
            else " — прямоугольная грань"
        )
        + ". Найдём его площадь, используя равенство параллельных рёбер:</p>"
    )
    rows = _measure(m, a) + _measure(m, b)
    coefficient = r"\frac{1}{2}\cdot " if factor == sp.Rational(1, 2) else ""
    rows += line(AREA + "=" + coefficient + label(a) + r"\cdot " + label(b))
    rows += line(
        AREA
        + "="
        + coefficient
        + bracket(va)
        + r"\cdot "
        + bracket(vb)
        + "="
        + value(factor * va * vb)
    )
    rows += (
        "<p>Высота совпадает с ребром "
        + html_name(label(height))
        + ":</p>"
        + _measure(m, height, prefix="h=")
    )
    return intro + rows, sp.simplify(factor * va * vb), h


def _base_volume(m, picture):
    kind = (
        "прямую треугольную призму"
        if m.solid.kind == "prism"
        else ("треугольную пирамиду" if len(m.solid.base) == 3 else "пирамиду")
    )
    body = (
        "<p>"
        + picture
        + (
            "Из рисунка видно, что многогранник составляет половину параллелепипеда. Он представляет собой "
            if m.solid.kind == "prism"
            else "Многогранник представляет собой "
        )
        + kind
        + ". "
    )
    rows, area, height = _base_height(m)
    body += rows
    coefficient = "" if m.solid.kind == "prism" else r"\frac{1}{3}\cdot "
    body += (
        "<p>Объём "
        + (
            "призмы равен произведению площади основания на высоту"
            if m.solid.kind == "prism"
            else "пирамиды равен трети произведения площади основания на высоту"
        )
        + ":</p>"
    )
    body += line(target(m) + "=" + coefficient + AREA + r"\cdot h")
    if m.solid.kind == "prism":
        body += "<p>Площадь основания равна половине площади соответствующей грани, а высота общая с параллелепипедом. Поэтому призма составляет половину его объёма:</p>"
        body += line(SOLID + r"=\frac{1}{2}" + BOX)
    return body + line(
        target(m)
        + "="
        + coefficient
        + bracket(area)
        + r"\cdot "
        + bracket(height)
        + "="
        + value(m.answer)
    )


def _relative(m, picture):
    factor = r"\frac{1}{2}" if len(m.solid.base) == 3 else "1"
    body = (
        "<p>"
        + picture
        + "Основание пирамиды "
        + html_name("".join(m.solid.base))
        + (
            " составляет половину грани"
            if len(m.solid.base) == 3
            else " совпадает с гранью"
        )
        + " параллелепипеда, а высота совпадает с соответствующей высотой параллелепипеда:</p>"
    )
    body += line(AREA + "=" + factor + FACE) + line(BOX + "=" + FACE + r"\cdot h")
    body += line(
        PYRAMID + r"=\frac{1}{3}" + AREA + r"\cdot h=" + value(m.solid.fraction) + BOX
    )
    return body + line(
        PYRAMID
        + "="
        + value(m.solid.fraction)
        + r"\cdot "
        + bracket(m.box_volume)
        + "="
        + value(m.answer)
    )


def _central(m, picture):
    body = (
        "<p>"
        + picture
        + "Искомый объём равен разности объёма параллелепипеда и четырёх угловых треугольных пирамид. Основание каждой можно выбрать половиной грани параллелепипеда; соответствующая высота у них общая:</p>"
    )
    body += line(CORNER + r"=\frac{1}{3}\cdot\frac{1}{2}" + BOX + r"=\frac{1}{6}" + BOX)
    body += "<p>Вычтем объёмы четырёх угловых пирамид:</p>"
    body += line(PYRAMID + "=" + BOX + "-4" + CORNER)
    body += line(PYRAMID + "=" + BOX + r"-\frac{4}{6}" + BOX + r"=\frac{1}{3}" + BOX)
    body += _box(m)
    return body + line(
        PYRAMID + r"=\frac{1}{3}\cdot " + bracket(m.box_volume) + "=" + value(m.answer)
    )


def _note(m):
    word = "призмы" if m.solid.kind == "prism" else "пирамиды"
    body = (
        "<p><b>Примечание.</b></p><p>Объём "
        + word
        + " можно также найти как долю объёма параллелепипеда. Отношение площадей оснований и совпадающая высота определяют эту долю; рассуждение справедливо и для наклонного параллелепипеда. Для данного многогранника:</p>"
    )
    if m.solid.kind == "central_tetrahedron":
        body = "<p><b>Примечание.</b></p><p>Разбиение на четыре угловые пирамиды сохраняется и для наклонного параллелепипеда. Поэтому доля искомого объёма равна одной трети:</p>"
    if m.solid.kind != "central_tetrahedron":
        coefficient = "" if m.solid.kind == "prism" else r"\frac{1}{3}\cdot "
        body += line(target(m) + "=" + coefficient + AREA + r"\cdot h")
    body += line(target(m) + "=" + value(m.solid.fraction) + BOX)
    body += (
        "<p>Заданный параллелепипед прямоугольный, его объём равен произведению измерений:</p>"
        if m.given
        else "<p>Подставим известный объём параллелепипеда:</p>"
    )
    return (
        body
        + _box(m)
        + line(
            target(m)
            + "="
            + value(m.solid.fraction)
            + r"\cdot "
            + bracket(m.box_volume)
            + "="
            + value(m.answer)
        )
    )


def render(m, picture, *, note=False):
    body = (
        _central(m, picture)
        if m.solid.kind == "central_tetrahedron"
        else _base_volume(m, picture)
        if m.given
        else _relative(m, picture)
    )
    return body + (_note(m) if note else "")
