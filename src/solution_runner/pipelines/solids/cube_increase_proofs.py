"""Expand the parent's surface difference and quadratic volume difference."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def _surface(m):
    k, delta = m.given
    ka = bracket(k) + r"\cdot a"
    return (
        "<p>Площадь поверхности исходного куба выражается через его ребро a:</p>"
        + line("S_0=6a^2")
        + "<p>При увеличении каждого ребра на заданную величину площадь S по сравнению с исходной площадью S₀ увеличится на:</p>"
        + line("S-S_0=6(a+" + bracket(k) + ")^2-6a^2")
        + line("S-S_0=6(a^2+2" + ka + "+" + bracket(k) + "^2)-6a^2")
        + line("S-S_0=12" + ka + "+6" + bracket(k) + "^2")
        + "<p>По условию это увеличение равно данной величине. Решим линейное уравнение:</p>"
        + line("12" + ka + "+6" + bracket(k) + "^2=" + value(delta))
        + line("12" + ka + "=" + value(delta) + "-6" + bracket(k) + "^2")
        + line(
            r"a=\frac{"
            + value(delta)
            + r"-6\cdot"
            + bracket(k)
            + r"^2}{12\cdot"
            + bracket(k)
            + "}="
            + value(m.answer)
        )
    )


def _volume(m):
    k, delta = m.given
    c = sp.simplify((k * k - delta / k) / 3)
    d = sp.simplify(k * k - 4 * c)
    negative = sp.simplify(-k - m.answer)
    return (
        "<p>Объём исходного куба с ребром a равен:</p>"
        + line("V_0=a^3")
        + "<p>Увеличение объёма после увеличения каждого ребра равно:</p>"
        + line("V-V_0=(a+" + bracket(k) + ")^3-a^3")
        + line(
            r"V-V_0=3\cdot"
            + bracket(k)
            + r"\cdot a^2+3\cdot"
            + bracket(k)
            + r"^2\cdot a+"
            + bracket(k)
            + "^3="
            + value(delta)
        )
        + "<p>Решим полученное квадратное уравнение, предварительно разделив на положительный коэффициент при a²:</p>"
        + line("a^2+" + bracket(k) + r"\cdot a-" + bracket(-c) + "=0")
        + line("D=" + bracket(k) + r"^2+4\cdot" + bracket(-c) + "=" + value(d))
        + line(
            r"a_1=\frac{-"
            + bracket(k)
            + r"+\sqrt{"
            + value(d)
            + "}}{2}="
            + value(m.answer)
        )
        + line(
            r"a_2=\frac{-"
            + bracket(k)
            + r"-\sqrt{"
            + value(d)
            + "}}{2}="
            + value(negative)
        )
        + "<p>Второй корень отрицателен и длиной ребра быть не может. Таким образом:</p>"
        + line("a=a_1=" + value(m.answer))
    )


def render(m):
    return _surface(m) if m.mode == "edge_from_surface_increase" else _volume(m)
