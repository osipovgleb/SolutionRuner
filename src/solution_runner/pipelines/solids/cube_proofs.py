"""Keep direct cube formulas, cubed diagonal and similarity parent methods."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from . import cube_increase_proofs, cube_section_proof


def _surface_volume(m):
    v = m.given[0]
    if m.mode == "surface_from_volume":
        a = sp.simplify(v ** sp.Rational(1, 3))
        return (
            "<p>Площадь поверхности куба выражается через его ребро a, а объём — через куб ребра:</p>"
            + line("S=6a^2")
            + line("V=a^3")
            + "<p>Найдём ребро, затем площадь поверхности:</p>"
            + line("a^3=V=" + value(v))
            + line(r"a=\sqrt[3]{" + value(v) + "}=" + value(a))
            + line(r"S=6\cdot" + bracket(a) + "^2=" + value(m.answer))
        )
    a = sp.sqrt(v / 6)
    return (
        "<p>Площадь поверхности куба со стороной a равна:</p>"
        + line("S=6a^2")
        + "<p>Выразим ребро через площадь поверхности:</p>"
        + line(r"a^2=\frac{S}{6}=\frac{" + value(v) + "}{6}")
        + line(r"a=\sqrt{\frac{" + value(v) + "}{6}}=" + value(a))
        + "<p>Объём куба равен:</p>"
        + line(r"V=a^3=\left(\sqrt{\frac{S}{6}}\right)^3")
        + line("V=" + bracket(a) + "^3=" + value(m.answer))
    )


def _diagonal(m):
    v = m.given[0]
    if m.mode == "diagonal_from_volume":
        d3 = sp.simplify(v * 3 * sp.sqrt(3))
        return (
            "<p>Если ребро куба равно a, то его объём и диагональ даются формулами:</p>"
            + line("V=a^3")
            + line(r"d=a\sqrt{3}")
            + "<p>Возведём формулу диагонали в куб и используем данный объём:</p>"
            + line(r"d^3=(a\sqrt{3})^3=a^3\cdot3\sqrt{3}")
            + line(r"d^3=" + bracket(v) + r"\cdot3\sqrt{3}=" + value(d3))
            + line(r"d=\sqrt[3]{" + value(d3) + "}=" + value(m.answer))
        )
    a = sp.simplify(v / sp.sqrt(3))
    intro = "<p>Диагональ куба в √3 раз больше его ребра. Найдём ребро:</p>"
    common = (
        intro
        + line(r"d=a\sqrt{3}")
        + line(r"a=\frac{d}{\sqrt{3}}")
        + line(r"a=\frac{" + value(v) + r"}{\sqrt{3}}=" + value(a))
    )
    if m.mode == "volume_from_diagonal":
        return (
            common
            + "<p>Тогда объём куба равен:</p>"
            + line("V=a^3")
            + line("V=" + bracket(a) + "^3=" + value(m.answer))
        )
    return (
        common
        + "<p>Тогда площадь поверхности куба равна:</p>"
        + line("S=6a^2")
        + line(r"S=6\cdot" + bracket(a) + "^2=" + value(m.answer))
    )


def _scaling(m):
    factor = m.given[0]
    if m.mode == "volume_factor":
        return (
            "<p>Объём куба с ребром a равен:</p>"
            + line("V=a^3")
            + "<p>После увеличения каждого ребра в данное число раз новый объём равен:</p>"
            + line(
                "V_1=("
                + bracket(factor)
                + r"\cdot a)^3="
                + bracket(factor)
                + r"^3\cdot a^3"
            )
            + "<p>Найдём, во сколько раз увеличился объём:</p>"
            + line(r"\frac{V_1}{V}=" + bracket(factor) + "^3=" + value(m.answer))
        )
    if m.mode == "surface_factor":
        return (
            "<p>Площади поверхностей подобных тел относятся как квадрат коэффициента подобия. При увеличении ребра коэффициент подобия равен:</p>"
            + line("k=" + value(factor))
            + "<p>Поэтому отношение новой площади поверхности к исходной равно:</p>"
            + line(r"\frac{S_1}{S_0}=k^2")
            + line(r"\frac{S_1}{S_0}=" + bracket(factor) + "^2=" + value(m.answer))
        )
    k = sp.simplify(factor ** sp.Rational(1, 3))
    return (
        "<p>Объёмы подобных тел относятся как куб коэффициента подобия, поэтому:</p>"
        + line(r"k^3=\frac{V_1}{V_2}=" + value(factor))
        + line(r"k=\sqrt[3]{" + value(factor) + "}=" + value(k))
        + "<p>Площади поверхностей подобных тел относятся как квадрат коэффициента подобия. Отношение большей площади к меньшей равно:</p>"
        + line(r"\frac{S_1}{S_2}=k^2")
        + line(r"\frac{S_1}{S_2}=" + bracket(k) + "^2=" + value(m.answer))
    )


def render(m, pictures):
    if m.mode == "midpoint_section_angle":
        return cube_section_proof.render(m, pictures)
    if m.mode.endswith("_increase"):
        return cube_increase_proofs.render(m)
    if m.mode in {"surface_from_volume", "volume_from_surface"}:
        return _surface_volume(m)
    if m.mode in {
        "diagonal_from_volume",
        "volume_from_diagonal",
        "surface_from_diagonal",
    }:
        return _diagonal(m)
    return _scaling(m)
