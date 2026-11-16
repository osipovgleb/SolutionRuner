"""Keep direct cube formulas, cubed diagonal and similarity parent methods."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section
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
    surface = m.given_text[0] if m.given_text else value(v)
    edge_cube = value(a) if a.is_Integer else bracket(a)
    return (
        "<p>Площадь поверхности куба со стороной a равна:</p>"
        + line("S=6a^2")
        + line("6a^2=" + surface)
        + line(r"a^2=\frac{" + surface + "}{6}=" + value(v / 6))
        + line(r"a=\sqrt{" + value(v / 6) + "}=" + value(a))
        + "<p>Объём куба равен:</p>"
        + line("V=a^3=" + edge_cube + "^3=" + value(m.answer))
    )


def _diagonal(m):
    v = m.given[0]
    if m.mode == "diagonal_from_volume":
        a = sp.simplify(v ** sp.Rational(1, 3))
        volume = m.given_text[0] if m.given_text else value(v)
        return (
            "<p>Найдём ребро куба по его объёму:</p>"
            + line("V=a^3")
            + line("a^3=" + volume)
            + line(r"a=\sqrt[3]{" + volume + "}=" + value(a))
            + '<p>Диагональ куба в <span data-inline-latex="\\sqrt{3}"></span> раз больше его ребра. Подставим найденное значение:</p>'
            + line(r"d=\sqrt{3}\cdot a")
            + line(r"d=\sqrt{3}\cdot " + value(a) + "=" + value(m.answer))
        )
    a = sp.simplify(v / sp.sqrt(3))
    intro = '<p>Диагональ куба в <span data-inline-latex="\\sqrt{3}"></span> раз больше его ребра. Найдём ребро:</p>'
    diagonal = m.given_text[0] if m.given_text else value(v)
    edge_power = value(a) if a.is_Integer else bracket(a)
    common = (
        intro
        + line(r"d=\sqrt{3}\cdot a")
        + line(diagonal + r"=\sqrt{3}\cdot a")
        + line(r"a=\frac{" + diagonal + r"}{\sqrt{3}}=" + value(a))
    )
    if m.mode == "volume_from_diagonal":
        return (
            common
            + "<p>Тогда объём куба равен:</p>"
            + line("V=a^3")
            + line("V=" + edge_power + "^3=" + value(m.answer))
        )
    return (
        common
        + "<p>Тогда площадь поверхности куба равна:</p>"
        + line("S=6a^2")
        + line(r"S=6\cdot" + edge_power + "^2=" + value(m.answer))
    )


def _scaling(m):
    factor = m.given[0]
    if m.mode in {"volume_factor", "surface_factor"}:
        factor_text = value(factor)
        factor_power = factor_text if factor.is_Integer else bracket(factor)
        if m.mode == "surface_factor":
            first = (
                "<p>Площадь поверхности куба с ребром a равна:</p>"
                + line("S_0=6a^2")
                + "<p>После увеличения каждого ребра новая площадь поверхности равна:</p>"
                + line("S_1=6(" + factor_text + r"\cdot a)^2=6\cdot" + factor_power + r"^2\cdot a^2")
                + "<p>Найдём, во сколько раз увеличилась площадь поверхности:</p>"
                + line(r"\frac{S_1}{S_0}=" + factor_power + "^2=" + value(m.answer))
            )
            alternative = (
                "<p>После увеличения каждого ребра кубы подобны; коэффициент подобия равен " + factor_text + ". Площади поверхностей подобных тел относятся как квадрат коэффициента подобия:</p>"
                + line(r"\frac{S_1}{S_0}=k^2")
                + line(r"\frac{S_1}{S_0}=" + factor_power + "^2=" + value(m.answer))
            )
            return solution_section("Решение", first) + solution_section("Альтернативное решение", alternative)
        first = (
            "<p>Объём куба с ребром a равен:</p>"
            + line("V=a^3")
            + "<p>После увеличения каждого ребра в данное число раз новый объём равен:</p>"
            + line(
                "V_1=("
                + factor_text
                + r"\cdot a)^3="
                + factor_power
                + r"^3\cdot a^3"
            )
            + "<p>Найдём, во сколько раз увеличился объём:</p>"
            + line(r"\frac{V_1}{V}=" + factor_power + "^3=" + value(m.answer))
        )
        alternative = (
            "<p>После увеличения каждого ребра кубы подобны; коэффициент подобия равен " + factor_text + ". Объёмы подобных тел относятся как куб коэффициента подобия:</p>"
            + line(r"\frac{V_1}{V}=k^3")
            + line(r"\frac{V_1}{V}=" + factor_power + "^3=" + value(m.answer))
        )
        return solution_section("Решение", first) + solution_section("Альтернативное решение", alternative)
    k = sp.simplify(factor ** sp.Rational(1, 3))
    k_power = value(k) if k.is_Integer else bracket(k)
    first = (
        "<p>Объёмы кубов с рёбрами a₁ и a₂ равны:</p>"
        + line(r"V_1=a_1^3")
        + line(r"V_2=a_2^3")
        + "<p>По условию отношение объёмов равно:</p>"
        + line(r"\frac{V_1}{V_2}=\frac{a_1^3}{a_2^3}=" + value(factor))
        + line(r"\frac{a_1}{a_2}=\sqrt[3]{" + value(factor) + "}=" + value(k))
        + line(r"a_1=" + value(k) + r"\cdot a_2")
        + "<p>Найдём отношение площадей поверхностей:</p>"
        + line(r"S_1=6a_1^2")
        + line(r"S_2=6a_2^2")
        + line(r"\frac{S_1}{S_2}=\frac{6(" + value(k) + r"\cdot a_2)^2}{6a_2^2}=" + k_power + "^2=" + value(m.answer))
    )
    alternative = (
        "<p>Кубы подобны. Объёмы подобных тел относятся как куб коэффициента подобия, поэтому:</p>"
        + line(r"k^3=\frac{V_1}{V_2}=" + value(factor))
        + line(r"k=\sqrt[3]{" + value(factor) + "}=" + value(k))
        + "<p>Площади поверхностей подобных тел относятся как квадрат коэффициента подобия. Отношение большей площади к меньшей равно:</p>"
        + line(r"\frac{S_1}{S_2}=k^2")
        + line(r"\frac{S_1}{S_2}=" + k_power + "^2=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section("Альтернативное решение", alternative)


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
