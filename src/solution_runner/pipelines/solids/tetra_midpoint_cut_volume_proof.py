"""Retain the source decomposition into PACNM and PQCN before taking the ratio."""

from ..probability.common import line
from .spatial_distance_proofs import parts
from .volume_section_format import bracket, value


def _claim(m):
    return (
        "<p>По условию точки M и N делят стороны AB и CB в одинаковом отношении, поэтому:</p>"
        + line(r"\frac{BM}{BA}=\frac{BN}{BC}=" + value(1 - m.q["fraction"]))
        + "<p>По теореме, обратной теореме Фалеса, MN ∥ AC. Отрезок PQ — средняя линия треугольника DAC, поэтому PQ ∥ AC. Следовательно, MN ∥ PQ, и точки P, Q, M и N лежат в одной плоскости.</p>"
    )


def _small_pyramid(m):
    q = m.q
    return (
        "<p>Пусть объём ABCD равен V. Пятигранник APMNCQ состоит из четырёхугольной пирамиды PACNM с основанием ACNM и треугольной пирамиды PQCN с основанием QCN. Выразим их объёмы через V.</p>"
        "<p>Расстояние от P до плоскости BCD вдвое меньше расстояния от A до этой плоскости. По отношению площадей треугольников с общим углом C:</p>"
        + line(
            r"\frac{S_{QCN}}{S_{BCD}}=\frac{CN}{CB}\cdot\frac{CQ}{CD}="
            + bracket(q["fraction"])
            + r"\cdot\frac12="
            + value(q["QCN_fraction"])
        )
        + line(
            r"V_{PQCN}=\frac12\cdot "
            + bracket(q["QCN_fraction"])
            + "V="
            + value(q["PQCN_volume"])
            + "V"
        )
    )


def _remainder(m):
    q = m.q
    return (
        "<p>Треугольники MBN и ABC подобны. Поэтому отношение их площадей равно квадрату отношения соответствующих сторон:</p>"
        + line(
            r"\frac{S_{MBN}}{S_{ABC}}=\left(\frac{BM}{BA}\right)^2="
            + bracket(1 - q["fraction"])
            + "^2="
            + value(q["small_base_fraction"])
        )
        + line(
            r"\frac{S_{ACNM}}{S_{ABC}}=1-"
            + bracket(q["small_base_fraction"])
            + "="
            + value(q["trapezoid_fraction"])
        )
        + "<p>Расстояние от P до плоскости ABC вдвое меньше расстояния от D до этой плоскости, следовательно:</p>"
        + line(
            r"V_{PACNM}=\frac12\cdot "
            + bracket(q["trapezoid_fraction"])
            + "V="
            + value(q["PACNM_volume"])
            + "V"
        )
        + line(
            r"V_{APMNCQ}=V_{PQCN}+V_{PACNM}=\left("
            + value(q["PQCN_volume"])
            + "+"
            + value(q["PACNM_volume"])
            + r"\right)V="
            + value(q["left_volume"])
            + "V"
        )
        + line(
            r"V_{BMNDPQ}=V-V_{APMNCQ}=\left(1-"
            + value(q["left_volume"])
            + r"\right)V="
            + value(q["right_volume"])
            + "V"
        )
        + line(
            r"\frac{V_{APMNCQ}}{V_{BMNDPQ}}=\frac{"
            + value(q["left_volume"])
            + "}{"
            + value(q["right_volume"])
            + "}="
            + value(m.answer)
        )
    )


def render(m, pictures):
    return parts(
        pictures.get("image_1", "") + _claim(m), _small_pyramid(m) + _remainder(m)
    )
