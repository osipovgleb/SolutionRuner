"""Preserve the parent Thales construction, then compute the requested quantity."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _ratio(m, pictures):
    q = m.q
    return (
        "<p>В плоскости BB₁D₁D через K проведём KL ∥ BD₁ до пересечения с B₁D₁. В верхнем основании прямая C₁L пересекает A₁B₁ в P. Плоскость KPC₁ содержит KL, параллельную BD₁; она и есть заданная плоскость α.</p>"
        + pictures.get("image_1", "")
        + "<p>Через A₁ проведём A₁M ∥ C₁P до пересечения с D₁B₁.</p>"
        + "<p>По теореме Фалеса в треугольнике B₁BD₁:</p>"
        + line(
            r"B_1K=BB_1-KB="
            + value(q["a"])
            + "-"
            + bracket(q["k"])
            + "="
            + value(q["d"])
        )
        + line(
            r"\frac{B_1L}{B_1D_1}=\frac{B_1K}{B_1B}=\frac{"
            + value(q["d"])
            + "}{"
            + value(q["a"])
            + "}"
        )
        + "<p>В верхнем основании треугольники D₁MA₁ и B₁LC₁ подобны, а D₁A₁ = B₁C₁, поэтому D₁M = B₁L. Снова применяя теорему Фалеса к параллельным A₁M и PC₁, получаем:</p>"
        + line(r"D_1M=B_1L=" + value(q["B1L"]))
        + line(
            r"ML=D_1B_1-D_1M-LB_1="
            + value(q["a"] * sp.sqrt(2))
            + "-2\\cdot "
            + bracket(q["B1L"])
            + "="
            + value(q["ML"])
        )
        + line(
            r"\frac{A_1P}{PB_1}=\frac{ML}{LB_1}=\frac{"
            + bracket(q["ML"])
            + "}{"
            + bracket(q["B1L"])
            + "}="
            + value(q["ratio"])
        )
        + line(r"A_1P:PB_1=" + value(q["p"]) + ":" + value(q["q"]))
    )


def _angle(m):
    q = m.q
    return (
        "<p>Пусть N — основание перпендикуляра B₁N к KC₁ в грани BB₁C₁C. Отрезок PB₁ перпендикулярен этой грани, поэтому B₁N — проекция PN. По теореме о трёх перпендикулярах PN ⟂ KC₁. Следовательно, ∠PNB₁ — линейный угол искомого двугранного угла.</p>"
        + line(
            r"PB_1=\frac{B_1L}{D_1L}\,D_1C_1=\frac{B_1K}{KB}\,AB=\frac{"
            + bracket(q["d"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{"
            + value(q["k"])
            + "}="
            + value(q["B1P"])
        )
        + "<p>Высоту B₁N найдём, вычисляя площадь прямоугольного треугольника KB₁C₁ двумя способами:</p>"
        + line(
            r"S_{KB_1C_1}=\frac{B_1K\cdot B_1C_1}{2}=\frac{"
            + bracket(q["d"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{2}="
            + value(q["triangle_area"])
        )
        + line(
            r"KC_1=\sqrt{B_1K^2+B_1C_1^2}=\sqrt{"
            + bracket(q["d"])
            + "^2+"
            + bracket(q["a"])
            + "^2}="
            + value(q["KC1"])
        )
        + line(
            r"B_1N=\frac{2S_{KB_1C_1}}{KC_1}=\frac{2\cdot "
            + bracket(q["triangle_area"])
            + "}{"
            + value(q["KC1"])
            + "}="
            + value(q["B1N"])
        )
        + line(
            r"\tan\angle PNB_1=\frac{PB_1}{B_1N}=\frac{"
            + bracket(q["B1P"])
            + "}{"
            + bracket(q["B1N"])
            + "}="
            + value(q["tan"])
        )
    )


def _volume(m):
    q = m.q
    return (
        "<p>Плоскость отсекает у вершины B₁ тетраэдр B₁KPC₁. Три его ребра при B₁ попарно перпендикулярны, поэтому объём равен одной шестой произведения их длин:</p>"
        + line(
            r"B_1P=\frac{B_1K}{KB}\,AB=\frac{"
            + bracket(q["d"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{"
            + value(q["k"])
            + "}="
            + value(q["B1P"])
        )
        + line(r"V_{B_1KPC_1}=\frac{B_1K\cdot B_1P\cdot B_1C_1}{6}")
        + line(
            r"V_{B_1KPC_1}=\frac{"
            + bracket(q["d"])
            + r"\cdot "
            + bracket(q["B1P"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{6}="
            + value(q["small_volume"])
        )
        + line(r"V_{\text{куба}}=AB^3=" + bracket(q["a"]) + "^3=" + value(q["a"] ** 3))
        + line(
            r"V_{\text{куба}}-V_{B_1KPC_1}="
            + value(q["a"] ** 3)
            + "-"
            + bracket(q["small_volume"])
            + "="
            + value(q["large_volume"])
        )
        + "<p>Полученный объём больше объёма отсечённого тетраэдра, следовательно, это большая часть куба.</p>"
    )


def render(m, pictures):
    if m.mode.endswith("volume"):
        return parts(_ratio(m, pictures), _volume(m))
    from .cube_parallel_cut_coordinates import render as coordinates

    return parts(_ratio(m, pictures), _angle(m)) + coordinates(m, pictures)
