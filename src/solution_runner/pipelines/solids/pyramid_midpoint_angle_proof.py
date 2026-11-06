"""Midline, projection, linear dihedral angle and the parent tangent calculation."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def render(m, pictures):
    q = m.q
    proof = (
        pictures.get("image_1", "")
        + "<p>Отрезок MK — средняя линия треугольника ASC, поэтому MK ∥ AC. Обозначим основание высоты пирамиды через O. Проекция SB на плоскость основания — OB. Диагонали квадрата перпендикулярны, следовательно, OB ⟂ AC. По теореме о трёх перпендикулярах направление SB перпендикулярно AC, а значит, и MK.</p>"
    )
    quantity = (
        "<p>Пусть Q — середина MK. Гомотетия с центром S и коэффициентом 1/2 переводит AC в MK, а O — в Q. Поэтому Q — середина SO. Плоскость SBD — плоскость симметрии пирамиды, поэтому BM = BK. В равнобедренном треугольнике BMK медиана BQ перпендикулярна MK. Плоскости BMK и ABC пересекаются по прямой через B, параллельной MK. Прямые BQ и BO перпендикулярны этой прямой, поэтому ∠QBO — линейный угол искомого двугранного угла.</p>"
        + line(
            r"BO=\frac{AB\sqrt2}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt2}{2}="
            + value(q["BO"])
        )
        + "<p>Боковые рёбра правильной пирамиды равны. В прямоугольном треугольнике SOB найдём высоту, затем её половину:</p>"
        + line(r"SO=\sqrt{SB^2-BO^2}")
        + line(
            r"SO=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["BO"])
            + "^2}="
            + value(q["H"])
        )
        + line(r"QO=\frac{SO}{2}=\frac{" + bracket(q["H"]) + "}{2}=" + value(q["QO"]))
        + "<p>В прямоугольном треугольнике QOB:</p>"
        + line(
            r"\tan\angle QBO=\frac{QO}{BO}=\frac{"
            + bracket(q["QO"])
            + "}{"
            + bracket(q["BO"])
            + "}="
            + value(q["tan"])
        )
    )
    return parts(proof, quantity)
