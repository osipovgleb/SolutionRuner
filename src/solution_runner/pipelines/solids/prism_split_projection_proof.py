"""The parent's perpendicular foot and two area computations find the prism angle."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _claim(m):
    if m.names[0] == "half":
        return "<p>Пусть N — середина AB. Поскольку ABC равнобедренный, медиана BM перпендикулярна AC. Треугольник AMB прямоугольный, поэтому его медиана NM равна половине гипотенузы AB, то есть NM = NB. Отрезок KN параллелен боковым рёбрам прямой призмы и перпендикулярен основанию. Прямоугольные треугольники KNM и KNB имеют общий катет KN и равные катеты NM и NB. Следовательно, их гипотенузы KM и KB равны.</p>"
    return "<p>Пусть N — середина AB, L — середина AC. В треугольнике ABL точки N и M — середины AB и AL. По теореме Фалеса MN ∥ BL. Высота BL равнобедренного треугольника ABC перпендикулярна AC, поэтому MN ⟂ AC. Прямая KN перпендикулярна основанию и направлению AC. Таким образом, плоскость KNM перпендикулярна AC, а значит, KM ⟂ AC.</p>"


def _distance(m):
    q = m.q
    quarter = m.names[0] == "quarter"
    if quarter:
        return (
            "<p>Проведём высоты MH и CE треугольников AMB и ABC к прямой AB. Из подобия треугольников AMH и ACE:</p>"
            + line(r"\frac{MH}{CE}=\frac{AM}{AC}=\frac14")
            + "<p>Вычисляя площадь треугольника ABC через разные основания, получим CE · AB = BL · AC. Поэтому:</p>"
            + line(r"MH=\frac{CE}{4}=\frac{BL\cdot AC}{4AB}")
            + line(
                r"BL=\sqrt{AB^2-AL^2}=\sqrt{"
                + bracket(q["a"])
                + "^2-"
                + bracket(q["b"] / 2)
                + "^2}="
                + value(q["base_height"])
            )
            + line(
                r"MH=\frac{"
                + bracket(q["base_height"])
                + r"\cdot "
                + bracket(q["b"])
                + r"}{4\cdot "
                + bracket(q["a"])
                + "}="
                + value(q["MH"])
            )
        )
    return (
        "<p>Проведём высоту MH треугольника AMB к AB. Найдём BM по теореме Пифагора:</p>"
        + line(
            r"BM=\sqrt{AB^2-AM^2}=\sqrt{"
            + bracket(q["a"])
            + "^2-"
            + bracket(q["b"] / 2)
            + "^2}="
            + value(q["base_height"])
        )
        + "<p>Вычисляя площадь прямоугольного треугольника AMB двумя способами, получим MH · AB = AM · BM:</p>"
        + line(
            r"MH=\frac{AM\cdot BM}{AB}=\frac{"
            + bracket(q["b"] / 2)
            + r"\cdot "
            + bracket(q["base_height"])
            + "}{"
            + bracket(q["a"])
            + "}="
            + value(q["MH"])
        )
    )


def _calculation(m):
    q = m.q
    quarter = m.names[0] == "quarter"
    foot, horizontal = ("N", q["base_height"] / 2) if quarter else ("N", q["a"] / 2)
    return (
        "<p>Прямая MH перпендикулярна AB и вертикальному направлению, поэтому MH ⟂ ABB₁. Значит, KH — проекция KM на плоскость ABB₁, а угол HKM — искомый.</p>"
        + _distance(m)
        + "<p>В прямоугольном треугольнике KM"
        + foot
        + " по теореме Пифагора:</p>"
        + line(
            "KM="
            + r"\sqrt{K"
            + foot
            + "^2+M"
            + foot
            + r"^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(horizontal)
            + "^2}="
            + value(q["KM"])
        )
        + "<p>Найдём синус угла HKM в прямоугольном треугольнике KHM:</p>"
        + line(
            r"\sin\angle HKM=\frac{MH}{KM}=\frac{"
            + bracket(q["MH"])
            + "}{"
            + bracket(q["KM"])
            + "}="
            + sp.latex(q["sine"])
        )
    )


def render(m, pictures):
    from .prism_split_vector_proof import render as vectors

    return parts(pictures.get("image_1", "") + _claim(m), _calculation(m)) + vectors(
        m, pictures
    )
