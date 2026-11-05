"""Use squared area ratios and cubed volume ratios without relying on saved answers."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _scale(m):
    q = m.ratio
    r = q if m.input_kind == "radius" else sp.Integer(1)
    h = q if m.input_kind == "height" else sp.Integer(1)
    l = q if m.input_kind == "slant" else sp.Integer(1)
    variable = {"radius": "r", "height": "h", "slant": "l"}[m.input_kind]
    fixed = (
        "h"
        if m.input_kind == "radius" and m.kind == "volume"
        else "l"
        if m.input_kind == "radius"
        else "r"
    )
    if m.kind == "volume":
        first = r"V_1=\frac{1}{3}\pi r_1^2h_1"
        second = r"V_2=\frac{1}{3}\pi r_2^2h_2"
        fraction = (
            r"\frac{V_2}{V_1}=\left(\frac{r_2}{r_1}\right)^2\cdot\frac{h_2}{h_1}="
            + bracket(r)
            + "^2"
            + r"\cdot"
            + bracket(h)
        )
        symbol = "V"
        ratio = r * r * h
    else:
        first = r"S_1=\pi r_1l_1"
        second = r"S_2=\pi r_2l_2"
        fraction = (
            r"\frac{S_2}{S_1}=\frac{r_2}{r_1}\cdot\frac{l_2}{l_1}="
            + bracket(r)
            + r"\cdot"
            + bracket(l)
        )
        symbol = "S"
        ratio = r * l
    return (
        "<p>Запишем формулы величин до и после изменения размеров:</p>"
        + line(first)
        + line(second)
        + "<p>По условию изменяется один размер, а другой остаётся прежним:</p>"
        + line(variable + "_2=" + bracket(q) + r"\cdot " + variable + "_1")
        + line(fixed + "_2=" + fixed + "_1")
        + "<p>Найдём отношение величин:</p>"
        + line(fraction)
        + line(r"\frac{" + symbol + "_2}{" + symbol + "_1}=" + value(ratio))
        + (
            line(
                r"\frac{"
                + symbol
                + "_1}{"
                + symbol
                + r"_2}=\frac{1}{"
                + value(ratio)
                + "}="
                + value(m.answer)
            )
            if q < 1
            else ""
        )
    )


def _liquid(m):
    amount = m.given[0]
    full = sp.simplify(amount / m.ratio**3)
    return (
        "<p>По рисунку сосуд направлен вершиной вниз. Жидкость образует меньший конус, подобный полному сосуду. Коэффициент подобия равен отношению высот:</p>"
        + line(r"k=\frac{h_1}{h_0}=" + value(m.ratio))
        + "<p>Объёмы подобных тел относятся как куб коэффициента подобия:</p>"
        + line(r"\frac{V_1}{V_0}=k^3")
        + line(r"V_0=\frac{V_1}{k^3}")
        + line(
            r"V_0=\frac{"
            + value(amount)
            + "}{"
            + bracket(m.ratio)
            + "^3}="
            + value(full)
        )
        + "<p>Из полного объёма вычтем уже налитый объём:</p>"
        + line(r"\Delta V=V_0-V_1")
        + line(r"\Delta V=" + value(full) + "-" + value(amount) + "=" + value(m.answer))
    )


def render(m):
    if m.mode == "scale":
        return _scale(m)
    if m.kind == "liquid":
        return _liquid(m)
    symbol = "V" if m.kind == "volume" else "S"
    power = 3 if m.kind == "volume" else 2
    ratio = m.ratio
    amount = m.given[0]
    row = (
        r"k=\frac{h_1}{h_0}=\frac{1}{2}"
        if len(m.given) == 1
        else r"k=\frac{h_1}{h_0}=\frac{"
        + value(m.given[1])
        + "}{"
        + value(m.given[1])
        + "+"
        + value(m.given[2])
        + "}="
        + value(ratio)
    )
    intro = (
        "<p>Меньший конус подобен большему. Сечение параллельно основанию, поэтому коэффициент подобия равен отношению расстояний от вершины:</p>"
        if m.kind != "section"
        else "<p>Сечение параллельно основанию, поэтому радиус круга сечения относится к радиусу основания как расстояния от вершины до их плоскостей:</p>"
    )
    explanation = (
        "<p>Объёмы подобных тел относятся как куб коэффициента подобия:</p>"
        if power == 3
        else "<p>Площади подобных фигур относятся как квадрат коэффициента подобия:</p>"
    )
    return (
        intro
        + line(row)
        + explanation
        + line(r"\frac{" + symbol + "_1}{" + symbol + "_0}=k^" + str(power))
        + line(symbol + "_1=k^" + str(power) + symbol + "_0")
        + line(symbol + "_1=" + bracket(ratio**power) + r"\cdot" + bracket(amount))
        + line(symbol + "_1=" + value(m.answer))
    )
