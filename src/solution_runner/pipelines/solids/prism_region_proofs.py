"""Preserve pyramid, subtraction and polygon-base methods for actual prism vertices."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _name(names):
    return "".join(names).replace("_1", "₁")


def _given(m):
    return line("B=" + value(m.given[0])) + line("H=" + value(m.given[1]))


def _final(m):
    return line(
        "V="
        + bracket(m.fraction)
        + r"\cdot"
        + bracket(m.given[0])
        + r"\cdot"
        + bracket(m.given[1])
    ) + line("V=" + value(m.answer))


def _pyramid(m):
    opening = (
        "<p>Искомый многогранник — пирамида с вершиной "
        + m.apex.replace("_1", "₁")
        + " и основанием "
        + _name(m.base)
        + ". Высота пирамиды совпадает с высотой правильной призмы, то есть с её боковым ребром:</p>"
    )
    if m.base_fraction == 1:
        return (
            opening
            + _given(m)
            + line("B_p=B")
            + line("h_p=H")
            + "<p>Основание пирамиды совпадает с основанием призмы. Объём пирамиды равен трети произведения площади основания на высоту:</p>"
            + line(r"V=\frac{1}{3}B_ph_p")
            + line(r"V=\frac{1}{3}BH")
            + _final(m)
        )
    return (
        opening
        + _given(m)
        + _sixth(m, "B_p")
        + "<p>Найдём объём пирамиды по площади её основания и общей высоте:</p>"
        + line(r"V=\frac{1}{3}B_pH")
        + _final(m)
    )


def _sixth(m, symbol):
    return (
        "<p>Правильный шестиугольник состоит из шести равносторонних треугольников со стороной a. Обозначим площадь одного через T. Треугольник "
        + _name(m.base)
        + " имеет две стороны a и угол 120° между ними; его площадь также равна T, поскольку sin 120° = sin 60°:</p>"
        + line(r"T=\frac{\sqrt{3}}{4}a^2")
        + line("B=6T")
        + line(symbol + "=T")
        + line(symbol + r"=\frac{B}{6}")
    )


def _subtract(m):
    count = len(m.removed)
    names = ", ".join(_name(t) for t in m.removed)
    volumes = "=V_2" if count == 2 else ""
    difference = "V_0-V_1" + ("-V_2" if count == 2 else "")
    coefficient = r"1-\frac{1}{3}" + (r"-\frac{1}{3}" if count == 2 else "")
    return (
        "<p>Искомый объём равен разности объёма призмы и "
        + (
            "объёмов двух треугольных пирамид "
            if count == 2
            else "объёма треугольной пирамиды "
        )
        + names
        + ". Площадь основания призмы и её высота равны:</p>"
        + _given(m)
        + line("V_0=BH")
        + "<p>У каждой вычитаемой пирамиды основание совпадает с целым основанием призмы, а высота равна её боковому ребру. Поэтому:</p>"
        + line("V_1" + volumes + r"=\frac{1}{3}BH")
        + "<p>Вычтем объёмы указанных пирамид:</p>"
        + line("V=" + difference)
        + line(r"V=\left(" + coefficient + r"\right)BH")
        + _final(m)
    )


def _quadrilateral(m):
    letters = "ABCDEF"
    omitted = [n for n in letters if n not in m.base]
    ears = tuple(
        letters[(letters.index(n) - 1) % 6] + n + letters[(letters.index(n) + 1) % 6]
        for n in omitted
    )
    note = "<p><b>Примечание.</b> Площадь правильного шестиугольника равна сумме площадей шести равносторонних треугольников со стороной a. У каждого отсечённого треугольника две стороны равны a, а угол между ними равен 120°. Поэтому его площадь равна площади одного такого равностороннего треугольника:</p>"
    return (
        "<p>Искомый многогранник — прямая четырёхугольная призма с основанием "
        + _name(m.base)
        + ". Из шестиугольника исключены треугольники "
        + " и ".join(ears)
        + ", каждый площадью в одну шестую площади основания. Поэтому:</p>"
        + line(r"B_p=B-\frac{B}{6}-\frac{B}{6}=\frac{2}{3}B")
        + line(
            r"B_p=\frac{2}{3}\cdot"
            + bracket(m.given[0])
            + "="
            + value(m.base_fraction * m.given[0])
        )
        + "<p>Высота выделенной прямой призмы совпадает с боковым ребром исходной призмы:</p>"
        + line("H=" + value(m.given[1]))
        + line("V=B_pH")
        + line(
            "V="
            + bracket(m.base_fraction * m.given[0])
            + r"\cdot"
            + bracket(m.given[1])
        )
        + line("V=" + value(m.answer))
        + note
        + line(r"T=\frac{1}{2}a^2\sin120^{\circ}=\frac{\sqrt{3}}{4}a^2")
        + line("B=6T")
        + line("S_" + r"{" + ears[0] + "}=S_{" + ears[1] + r"}=\frac{B}{6}")
    )


def _prism(m):
    if m.base_fraction != sp.Rational(1, 6):
        return _quadrilateral(m)
    return (
        "<p>Искомый многогранник — прямая треугольная призма с основанием "
        + _name(m.base)
        + ". Найдём площадь этого основания:</p>"
        + _sixth(m, "B_p")
        + "<p>Высота выделенной призмы равна боковому ребру исходной призмы. Объём равен произведению площади основания на высоту:</p>"
        + line("H=" + value(m.given[1]))
        + line("V=B_pH")
        + _final(m)
    )


METHODS = {"pyramid": _pyramid, "subtract": _subtract, "prism": _prism}


def render(m):
    return METHODS[m.method](m)
