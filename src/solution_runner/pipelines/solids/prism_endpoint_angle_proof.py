"""The parent converse-Pythagoras proof followed by the linear base angle."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def render(m, pictures):
    q = m.q
    proof = (
        pictures.get("image_1", "")
        + "<p>Сечение — треугольник ATC₁: его стороны соединяют три заданные точки в гранях призмы. Найдём его стороны. В прямоугольнике ABB₁A₁, правильном треугольнике A₁B₁C₁ и прямоугольнике ACC₁A₁ применим теорему Пифагора:</p>"
        + line(
            r"A_1T=\frac{A_1B_1}{2}=\frac{" + value(q["a"]) + "}{2}=" + value(q["A1T"])
        )
        + line(
            r"AT=\sqrt{AA_1^2+A_1T^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["A1T"])
            + "^2}="
            + value(q["AT"])
        )
        + line(
            r"TC_1=\sqrt{A_1C_1^2-A_1T^2}=\sqrt{"
            + bracket(q["a"])
            + "^2-"
            + bracket(q["A1T"])
            + "^2}="
            + value(q["TC1"])
        )
        + line(
            r"AC_1=\sqrt{AA_1^2+A_1C_1^2}=\sqrt{"
            + bracket(q["height"])
            + "^2+"
            + bracket(q["a"])
            + "^2}="
            + value(q["AC1"])
        )
        + line(
            r"AT^2+TC_1^2="
            + value(q["AT"] ** 2)
            + "+"
            + value(q["TC1"] ** 2)
            + "="
            + value(q["AC1"] ** 2)
            + r"=AC_1^2"
        )
        + "<p>По теореме, обратной теореме Пифагора, треугольник ATC₁ прямоугольный, с прямым углом при T.</p>"
    )
    quantity = (
        "<p>Прямая C₁T перпендикулярна AT и A₁T. Поэтому ∠A₁TA — линейный угол между плоскостью сечения и верхним основанием. Верхнее основание параллельно ABC, следовательно, этот угол равен искомому углу с плоскостью ABC.</p>"
        + line(r"\tan\angle A_1TA=\frac{AA_1}{A_1T}")
        + line(
            r"\tan\angle A_1TA=\frac{"
            + value(q["height"])
            + "}{"
            + value(q["A1T"])
            + "}="
            + value(q["tan"])
        )
    )
    return parts(proof, quantity)
