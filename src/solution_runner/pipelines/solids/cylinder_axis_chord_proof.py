"""Share the diametral right-angle proof while retaining the parent's coordinate method."""

import sympy as sp

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import bracket, value


def _claim():
    return (
        "<p>Рассмотрим плоскость, проходящую через ось цилиндра и AC₁. Пусть C — проекция C₁ на основание с точкой A. Тогда CC₁ — образующая цилиндра. Отрезок AC проходит через центр основания, поэтому является его диаметром. Вписанный угол ABC, опирающийся на диаметр, прямой.</p>"
        "<p>Образующая CC₁ перпендикулярна плоскости основания и направлению AB. Таким образом, AB перпендикулярна двум пересекающимся направлениям BC и CC₁ плоскости BCC₁. Следовательно, AB ⟂ (BCC₁) и AB ⟂ BC₁. Значит, угол ABC₁ прямой.</p>"
    )


def _diameter(m):
    q = m.q
    return (
        "<p>Треугольник ABC прямоугольный, причём BC = B₁C₁. По теореме Пифагора:</p>"
        + line(r"AC=\sqrt{AB^2+BC^2}=\sqrt{AB^2+B_1C_1^2}")
        + line(
            r"AC=\sqrt{"
            + bracket(q["AB"])
            + "^2+"
            + bracket(q["B1C1"])
            + "^2}="
            + value(q["diameter"])
        )
    )


def _angle(m):
    q = m.q
    return (
        "<p>Прямые BB₁ и CC₁ параллельны, поэтому искомый угол равен острому углу AC₁C прямоугольного треугольника ACC₁.</p>"
        + _diameter(m)
        + line(r"\tan\angle AC_1C=\frac{AC}{CC_1}=\frac{AC}{BB_1}")
        + line(
            r"\tan\angle AC_1C=\frac{"
            + value(q["diameter"])
            + "}{"
            + value(q["H"])
            + "}="
            + value(q["tangent"])
        )
        + line(r"\angle AC_1C=\arctan " + bracket(q["tangent"]))
    )


def _distance(m):
    q = m.q
    return (
        "<p>Треугольник ABC₁ прямоугольный. Пусть K — основание перпендикуляра из B на гипотенузу AC₁. Искомое расстояние равно высоте BK. Сначала найдём стороны:</p>"
        + line(
            r"BC_1=\sqrt{BB_1^2+B_1C_1^2}=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(q["B1C1"])
            + "^2}="
            + value(q["BC1"])
        )
        + line(
            r"AC_1=\sqrt{AB^2+BC_1^2}=\sqrt{"
            + bracket(q["AB"])
            + "^2+"
            + bracket(q["BC1"])
            + "^2}="
            + value(q["AC1"])
        )
        + "<p>Выразим удвоенную площадь треугольника через произведение катетов и через гипотенузу с высотой:</p>"
        + line(r"BK=\frac{AB\cdot BC_1}{AC_1}")
        + line(
            r"BK=\frac{"
            + bracket(q["AB"])
            + r"\cdot "
            + bracket(q["BC1"])
            + "}{"
            + value(q["AC1"])
            + "}="
            + value(m.answer)
        )
    )


def _area(m):
    q = m.q
    return (
        _diameter(m)
        + "<p>Отрезок AC — диаметр основания цилиндра. Поэтому длина окружности основания равна:</p>"
        + line(
            r"L=\pi AC=\pi\cdot "
            + bracket(q["diameter"])
            + "="
            + value(q["diameter"] * sp.pi)
        )
        + "<p>Площадь боковой поверхности равна произведению длины окружности основания на высоту цилиндра:</p>"
        + line(
            r"S_{\mathrm{бок}}=L\cdot BB_1="
            + bracket(q["diameter"] * sp.pi)
            + r"\cdot "
            + bracket(q["H"])
            + "="
            + value(m.answer)
        )
    )


def _coordinates(picture):
    return (
        "<p><b>Другое решение пункта а).</b></p>"
        + picture
        + "<p>Введём координаты, как на рисунке. Пусть BB₁ = h, радиус основания равен r. Параметр α задаёт положение B на окружности. Тогда:</p>"
        + line(r"A(r;0;0),\quad B(r\sin\alpha;r\cos\alpha;0),\quad C_1(-r;0;h)")
        + line(r"\overrightarrow{AB}=(r\sin\alpha-r;r\cos\alpha;0)")
        + line(r"\overrightarrow{BC_1}=(-r\sin\alpha-r;-r\cos\alpha;h)")
        + "<p>Вычислим скалярное произведение:</p>"
        + line(
            r"\overrightarrow{AB}\cdot\overrightarrow{BC_1}=r(\sin\alpha-1)\cdot(-r)(\sin\alpha+1)-r^2\cos^2\alpha"
        )
        + line(
            r"\overrightarrow{AB}\cdot\overrightarrow{BC_1}=r^2(1-\sin^2\alpha)-r^2\cos^2\alpha=0"
        )
        + "<p>Векторы ненулевые и перпендикулярны. Следовательно, угол ABC₁ прямой.</p>"
    )


def render(m, pictures):
    calculation = {"angle": _angle, "distance": _distance, "lateral_area": _area}[
        m.names[0]
    ]
    result = parts(pictures.get("image_1", "") + _claim(), calculation(m))
    if m.symbols.get("coordinate_method") == "yes":
        result += _coordinates(pictures.get("image_2", ""))
    return result
