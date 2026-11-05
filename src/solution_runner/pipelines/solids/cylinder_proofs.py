"""Expand the parents' displacement, scale and lateral-area methods."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import cylinder_cut_proofs


def _displacement(m):
    if m.kind == "factor":
        return _factor_displacement(m)
    volume, height, delta = m.given
    ratio = sp.simplify(delta / height)
    return (
        "<p>Объём детали равен объёму вытесненной ею жидкости. В цилиндрическом сосуде объём пропорционален высоте при постоянной площади основания:</p>"
        + line("V_0=Bh_0")
        + line("V_1=B(h_0+\\Delta h)")
        + "<p>Вычтем исходный объём. Для полностью погружённой детали получаем:</p>"
        + line(r"V=V_1-V_0=B\Delta h")
        + line(r"V=\frac{\Delta h}{h_0}V_0")
        + line(
            r"V=\frac{"
            + value(delta)
            + "}{"
            + value(height)
            + r"}\cdot"
            + bracket(volume)
        )
        + line(
            "V=" + bracket(ratio) + r"\cdot" + bracket(volume) + "=" + value(m.answer)
        )
    )


def _factor_displacement(m):
    volume, factor = m.given
    change = sp.simplify(factor - 1)
    return (
        "<p>Объём детали равен объёму вытесненной ею воды. В цилиндрическом сосуде площадь сечения B постоянна, поэтому объём жидкости пропорционален её высоте:</p>"
        + line("V_0=Bh_0")
        + line("h_1=kh_0")
        + line("V_1=Bh_1=kV_0")
        + "<p>Вычтем исходный объём воды. Увеличение объёма обусловлено погружением детали:</p>"
        + line("V=V_1-V_0=(k-1)V_0")
        + line("k-1=" + value(factor) + "-1=" + value(change))
        + line(r"V=\left(" + value(factor) + r"-1\right)\cdot" + bracket(volume))
        + line(
            "V=" + bracket(change) + r"\cdot" + bracket(volume) + "=" + value(m.answer)
        )
    )


def _transfer(m):
    height, ratio = m.given
    return (
        "<p>Объём цилиндрического сосуда выражается через диаметр и высоту жидкости. При переливании объём сохраняется:</p>"
        + line(r"V=\frac{\pi d_1^2}{4}h_1=\frac{\pi d_2^2}{4}h_2")
        + line("d_2=" + bracket(ratio) + r"\cdot d_1")
        + "<p>Выразим новую высоту. Площадь основания изменяется как квадрат диаметра:</p>"
        + line(r"h_2=h_1\left(\frac{d_1}{d_2}\right)^2")
        + line(r"h_2=\frac{h_1}{" + bracket(ratio) + "^2}")
        + line(
            r"h_2=\frac{"
            + value(height)
            + "}{"
            + value(ratio**2)
            + "}="
            + value(m.answer)
        )
    )


def _volume_ratio(m):
    volume, kh, kr = m.given
    return (
        "<p>Пусть объёмы цилиндров выражаются через радиусы оснований R₁, R₂ и высоты H₁, H₂:</p>"
        + line(r"V_1=\pi R_1^2 H_1")
        + line(r"V_2=\pi R_2^2 H_2")
        + "<p>По условию высоты и радиусы связаны соотношениями:</p>"
        + line("H_2=" + bracket(kh) + r"\cdot H_1")
        + line("R_2=" + bracket(kr) + r"\cdot R_1")
        + "<p>Выразим объём второго цилиндра через объём первого:</p>"
        + line(
            r"V_2=\pi\left("
            + bracket(kr)
            + r"\cdot R_1\right)^2\cdot"
            + bracket(kh)
            + r"\cdot H_1"
        )
        + line("V_2=" + bracket(kr**2 * kh) + r"\cdot V_1")
        + line(
            "V_2="
            + bracket(kr**2 * kh)
            + r"\cdot"
            + bracket(volume)
            + "="
            + value(m.answer)
        )
    )


def _lateral(m):
    first, height = m.given
    circumference = 2 * sp.pi * first if m.kind == "radius" else first
    surface = sp.simplify(circumference * height)
    rows = (
        "<p>Площадь боковой поверхности цилиндра равна произведению длины окружности основания на высоту:</p>"
        + line(r"S=2\pi rh")
        + line(r"C=2\pi r")
        + line("S=Ch")
    )
    if m.kind == "radius":
        rows += line("r=" + value(first)) + line(
            r"C=2\pi\cdot" + bracket(first) + "=" + value(circumference)
        )
    else:
        rows += line("C=" + value(first))
    rows += (
        "<p>Подставим данные и вычислим площадь:</p>"
        + line("h=" + value(height))
        + line(
            "S="
            + bracket(circumference)
            + r"\cdot"
            + bracket(height)
            + "="
            + value(surface)
        )
    )
    return rows + (
        r"<p>По условию требуется площадь, делённая на π:</p>"
        + line(r"\frac{S}{\pi}=\frac{" + value(surface) + r"}{\pi}=" + value(m.answer))
        if m.divide_pi
        else ""
    )


def _axial(m):
    area = m.given[0]
    rows = (
        "<p>Осевое сечение цилиндра — прямоугольник со сторонами 2r и h. Его площадь равна:</p>"
        + line("A=2rh")
        + line("A=" + value(area))
        + "<p>Тогда площадь боковой поверхности:</p>"
        + line(r"S=2\pi rh")
        + line(r"S=\pi A=" + bracket(area) + r"\pi")
    )
    return (
        rows + line(r"\frac{S}{\pi}=" + value(m.answer))
        if m.divide_pi
        else rows + line("S=" + value(m.answer))
    )


def _height(m, picture):
    if m.kind == "circumference":
        circumference, surface = m.given
        rows = (
            "<p>"
            + picture
            + "Площадь боковой поверхности цилиндра равна произведению длины окружности основания на высоту:</p>"
            + line("S=Ch")
            + line("C=" + value(circumference))
            + line("S=" + value(surface))
        )
        return (
            rows
            + "<p>Поэтому высота цилиндра равна:</p>"
            + line(r"h=\frac{S}{C}")
            + line(
                r"h=\frac{"
                + value(surface)
                + "}{"
                + value(circumference)
                + "}="
                + value(m.answer)
            )
        )
    surface, diameter = m.given
    return (
        "<p>"
        + picture
        + "Площадь боковой поверхности цилиндра находится по формуле:</p>"
        + line(r"S=2\pi rh")
        + line(r"r=\frac{d}{2}")
        + line(r"S=\pi dh")
        + "<p>Выразим высоту и подставим данные:</p>"
        + line(r"h=\frac{S}{\pi d}")
        + line(
            r"h=\frac{"
            + value(surface)
            + r"}{\pi\cdot"
            + bracket(diameter)
            + "}="
            + value(m.answer)
        )
    )


def _diameter(m, picture):
    surface, height = m.given
    return (
        ("<p>" + picture + "</p>" if picture else "")
        + "<p>Площадь боковой поверхности цилиндра находится по формуле:</p>"
        + line(r"S=2\pi rh")
        + line(r"r=\frac{S}{2\pi h}")
        + "<p>Диаметр равен удвоенному радиусу:</p>"
        + line("d=2r")
        + line(r"d=2\frac{S}{2\pi h}=\frac{S}{\pi h}")
        + line(
            r"d=\frac{"
            + value(surface)
            + r"}{\pi\cdot"
            + bracket(height)
            + "}="
            + value(m.answer)
        )
    )


def render(m, picture=""):
    if m.mode == "height":
        return _height(m, picture)
    if m.mode == "diameter":
        return _diameter(m, picture)
    return {
        "sector": cylinder_cut_proofs.sector,
        "stepped": cylinder_cut_proofs.stepped,
        "annular": cylinder_cut_proofs.annular,
        "displacement": _displacement,
        "transfer": _transfer,
        "volume_ratio": _volume_ratio,
        "lateral": _lateral,
        "axial_lateral": _axial,
    }[m.mode](m)
