"""Expand the parent's surface difference and quadratic volume difference."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _surface(m):
    k, delta = m.given
    k_text = value(k)
    return (
        "<p>Площадь поверхности исходного куба выражается через его ребро a:</p>"
        + line("S_0=6a^2")
        + "<p>После увеличения ребра площадь поверхности станет равной:</p>"
        + line("S_1=6(a+" + k_text + ")^2")
        + "<p>По условию новая площадь больше исходной на заданную величину. Составим уравнение:</p>"
        + line("6(a+" + k_text + ")^2=6a^2+" + value(delta))
        + "<p>Раскроем скобки и сократим квадратные члены. Получим линейное уравнение:</p>"
        + line("6(a^2+2" + r"\cdot " + k_text + r"\cdot a+" + k_text + r"\cdot " + k_text + ")=6a^2+" + value(delta))
        + line("6a^2+" + value(12 * k) + r"\cdot a+" + value(6 * k**2) + "=6a^2+" + value(delta))
        + line(value(12 * k) + r"\cdot a+" + value(6 * k**2) + "=" + value(delta))
        + line(value(12 * k) + r"\cdot a=" + value(delta) + "-" + value(6 * k**2))
        + line(value(12 * k) + r"\cdot a=" + value(delta - 6 * k**2))
        + line(
            r"a=\frac{"
            + value(delta - 6 * k**2)
            + "}{"
            + value(12 * k)
            + "}="
            + value(m.answer)
        )
    )


def _volume(m):
    k, delta = m.given
    c = sp.simplify((k * k - delta / k) / 3)
    d = sp.simplify(k * k - 4 * c)
    negative = sp.simplify(-k - m.answer)
    def term(coefficient, variable):
        return variable if coefficient == 1 else value(coefficient) + r"\cdot " + variable

    quadratic = term(3 * k, "a^2") + "+" + term(3 * k**2, "a")
    normalized = "a^2+" + term(k, "a") + "-" + value(-c)
    return (
        "<p>Объёмы исходного куба и куба с увеличенным ребром равны:</p>"
        + line("V_0=a^3")
        + line("V_1=(a+" + value(k) + ")^3")
        + '<p>По условию новый объём больше исходного на <span data-inline-latex="' + value(delta) + '"></span>. Составим уравнение:</p>'
        + line("(a+" + value(k) + ")^3=a^3+" + value(delta))
        + line("a^3+" + quadratic + "+" + value(k**3) + "=a^3+" + value(delta))
        + line("a^3+" + quadratic + "+" + value(k**3) + "-a^3-" + value(delta) + "=0")
        + line(quadratic + "-" + value(delta - k**3) + "=0")
        + line(normalized + "=0")
        + line("D=" + value(k**2) + r"+4\cdot" + value(-c) + "=" + value(d))
        + line(
            r"\left[\begin{aligned}a&=\frac{-"
            + value(k)
            + r"+\sqrt{"
            + value(d)
            + "}}{2}="
            + value(m.answer)
            + r"\\a&=\frac{-"
            + value(k)
            + r"-\sqrt{"
            + value(d)
            + "}}{2}="
            + value(negative)
            + r"\quad\text{— такого не может быть}\end{aligned}\right."
        )
    )


def render(m):
    return _surface(m) if m.mode == "edge_from_surface_increase" else _volume(m)
