"""Parallel faces first, then the parent's perpendicular-foot linear angle."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim():
    return "<p>Четырёхугольники BB₁D₁D и A₁BCD₁ — параллелограммы, поэтому BD ∥ B₁D₁ и A₁B ∥ CD₁. В каждой из рассматриваемых плоскостей эти две прямые пересекаются. Их следы в плоскости основания — BD и параллельная ей прямая через C — различны. По признаку параллельности плоскостей A₁BD ∥ B₁CD₁. Для этого рассуждения прямоугольность параллелепипеда не требуется.</p>"


def _side(m):
    q = m.q
    intro = (
        "<p>Заменим CDD₁ параллельной ей плоскостью ABB₁A₁. Их угол с BDA₁ одинаков. Общая прямая ABB₁A₁ и BDA₁ — BA₁. "
        + (
            "Пусть E — середина BA₁. Поскольку AB = AA₁, треугольник ABA₁ равнобедренный, поэтому AE ⟂ BA₁. "
            if sp.simplify(q["a"] - q["height"]) == 0
            else "Опустим из A перпендикуляр AE к BA₁. "
        )
        + "Проекция DE на грань ABB₁A₁ — AE, поэтому по теореме о трёх перпендикулярах DE ⟂ BA₁. Угол DEA — линейный угол искомого двугранного угла.</p>"
    )
    helper = (
        line(r"AE=\frac{BA_1}{2}=\frac{\sqrt{AB^2+AA_1^2}}{2}")
        if sp.simplify(q["a"] - q["height"]) == 0
        else line(r"AE=\frac{AB\cdot AA_1}{BA_1}")
    )
    return (
        intro
        + helper
        + line(r"AE=" + value(q["helper"]))
        + line(
            r"\tan\angle DEA=\frac{AD}{AE}=\frac{"
            + bracket(q["b"])
            + "}{"
            + bracket(q["helper"])
            + "}="
            + value(q["tan"])
        )
    )


def _top(m):
    q = m.q
    intro = (
        "<p>Вместо верхнего основания возьмём параллельную ему плоскость ABC. Общая прямая ABC и ACD₁ — AC. "
        + (
            "Пусть E — середина AC. В квадрате ABCD диагонали перпендикулярны, поэтому DE ⟂ AC. "
            if sp.simplify(q["a"] - q["b"]) == 0
            else "Пусть E — основание перпендикуляра из D на AC. "
        )
        + "По теореме о трёх перпендикулярах D₁E ⟂ AC. Значит, угол DED₁ — линейный угол искомого двугранного угла.</p>"
    )
    helper = (
        line(r"DE=\frac{BD}{2}=\frac{\sqrt{AB^2+AD^2}}{2}")
        if sp.simplify(q["a"] - q["b"]) == 0
        else line(r"DE=\frac{AD\cdot DC}{AC}")
    )
    return (
        intro
        + helper
        + line(r"DE=" + value(q["helper"]))
        + line(
            r"\tan\angle DED_1=\frac{DD_1}{DE}=\frac{"
            + bracket(q["height"])
            + "}{"
            + bracket(q["helper"])
            + "}="
            + value(q["tan"])
        )
    )


def _base(m):
    q = m.q
    return (
        "<p>Общая прямая ABC и A₁DB — BD. Опустим из A перпендикуляр AH на BD. По теореме о трёх перпендикулярах A₁H также перпендикулярна BD, поэтому угол A₁HA — линейный угол искомого двугранного угла.</p>"
        + "<p>Найдём высоту прямоугольного треугольника BAD через его площадь:</p>"
        + line(
            r"BD=\sqrt{AB^2+AD^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["b"])
            + "^2}="
            + value(q["hypotenuse"])
        )
        + line(
            r"AH=\frac{AB\cdot AD}{BD}=\frac{"
            + bracket(q["a"])
            + r"\cdot "
            + bracket(q["b"])
            + "}{"
            + value(q["hypotenuse"])
            + "}="
            + value(q["helper"])
        )
        + line(
            r"\tan\angle A_1HA=\frac{AA_1}{AH}=\frac{"
            + bracket(q["height"])
            + "}{"
            + bracket(q["helper"])
            + "}="
            + value(q["tan"])
        )
    )


def render(m, pictures):
    picture = pictures.get("image_1", pictures.get("box_distance_solution", ""))
    calculation = {"side": _side, "top": _top, "base": _base}[m.names[0]](m)
    return parts(picture + _claim(), calculation)
