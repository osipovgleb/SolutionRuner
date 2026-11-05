"""Expand reviewed cone formulas with the actual child's dimensions and target."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .cone_cut_proofs import render as sector
from .cone_dimension_proofs import dimensions
from .cone_similarity_proofs import render as similar


def _quotient(symbol, answer):
    return "<p>В ответе укажем величину, делённую на π:</p>" + line(
        r"\frac{"
        + symbol
        + r"}{\pi}=\frac{"
        + value(answer * sp.pi)
        + r"}{\pi}="
        + value(answer)
    )


def _lateral(m):
    circumference, slant = m.given
    return (
        "<p>Площадь боковой поверхности конуса выражается через радиус основания и образующую. Длина окружности основания равна:</p>"
        + line(r"C=2\pi r")
        + line(r"r=\frac{C}{2\pi}")
        + "<p>Подставим это выражение в формулу площади:</p>"
        + line(r"S=\pi rl")
        + line(r"S=\frac{1}{2}Cl")
        + line(
            r"S=\frac{1}{2}\cdot"
            + bracket(circumference)
            + r"\cdot"
            + bracket(slant)
            + "="
            + value(m.answer)
        )
    )


def _geometry(m):
    if m.kind == "lateral":
        return _lateral(m)
    r, h, l = m.radius, m.height, m.slant
    rows = dimensions(m)
    if m.kind in {"height", "slant"}:
        return rows
    if m.kind == "diameter":
        return (
            rows
            + "<p>Диаметр основания равен удвоенному радиусу:</p>"
            + line("d=2r")
            + line(r"d=2\cdot" + bracket(r) + "=" + value(m.answer))
        )
    if m.kind == "volume":
        return (
            rows
            + "<p>Объём конуса равен трети произведения площади основания на высоту:</p>"
            + line(r"V=\frac{1}{3}\pi r^2h")
            + line(r"V=\frac{1}{3}\cdot\pi\cdot" + bracket(r) + r"^2\cdot" + bracket(h))
            + line("V=" + value(sp.pi * m.answer))
            + _quotient("V", m.answer)
        )
    if m.kind == "total":
        return (
            rows
            + "<p>Площадь полной поверхности складывается из площади основания и площади боковой поверхности:</p>"
            + line(r"S=\pi r^2+\pi rl=\pi r(r+l)")
            + line(
                r"S=\pi\cdot"
                + bracket(r)
                + r"\left("
                + value(r)
                + "+"
                + value(l)
                + r"\right)"
            )
            + line("S=" + value(sp.pi * m.answer))
            + _quotient("S", m.answer)
        )
    return (
        rows
        + "<p>Осевое сечение — треугольник с основанием 2r и высотой h:</p>"
        + line(r"A=\frac{1}{2}(2r)h=rh")
        + line("A=" + bracket(r) + r"\cdot" + bracket(h) + "=" + value(m.answer))
    )


def render(m, picture=""):
    return ("<p>" + picture + "</p>" if picture else "") + (
        {
            "geometry": _geometry,
            "scale": similar,
            "similarity": similar,
            "sector": sector,
        }[m.mode](m)
    )
