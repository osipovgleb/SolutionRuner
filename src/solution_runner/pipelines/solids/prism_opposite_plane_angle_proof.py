"""Correct opposite vertices, then the parent similarity and altitude method."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _proof(m, pictures):
    first, second, rectangle = (
        ("A₁", "C", "A₁BCD₁") if m.names == ("A_1", "C") else ("A", "C₁", "ABC₁D₁")
    )
    return (
        pictures.get("image_1", "")
        + "<p>Четырёхугольник "
        + rectangle
        + " — прямоугольник, поэтому его диагонали "
        + first
        + second
        + " и BD₁ пересекаются в общей середине O. Точка O лежит в плоскости BED₁. Пусть P и L — проекции "
        + first
        + " и "
        + second
        + " соответственно на эту плоскость. Прямоугольные треугольники P"
        + first
        + "O и L"
        + second
        + "O равны по гипотенузе и острому углу: "
        + first
        + "O = "
        + second
        + "O, а углы при O равны как углы между одной прямой "
        + first
        + second
        + " и её проекцией. Следовательно, "
        + first
        + "P = "
        + second
        + "L, то есть точки "
        + first
        + " и "
        + second
        + " равноудалены от плоскости BED₁.</p>"
    )


def render(m, pictures):
    q = m.q
    proof = _proof(m, pictures)
    quantity = (
        "<p>Продлим D₁E за E и DA за A до пересечения в K. Плоскости ABC и BED₁ пересекаются по KB. Опустим EH ⟂ KB. Проекция EH на основание — AH; по теореме о трёх перпендикулярах AH ⟂ KB. Поэтому угол EHA — линейный угол искомого двугранного угла.</p>"
        + line(
            r"AE=\frac{"
            + value(dict(m.given)["p"])
            + "}{"
            + value(dict(m.given)["p"] + dict(m.given)["q"])
            + r"}AA_1="
            + value(q["AE"])
        )
        + line(
            r"EA_1=AA_1-AE="
            + value(q["height"])
            + "-"
            + bracket(q["AE"])
            + "="
            + value(q["A1E"])
        )
        + "<p>Треугольники A₁D₁E и AKE подобны, поэтому:</p>"
        + line(
            r"AK=\frac{AE}{EA_1}A_1D_1=\frac{"
            + bracket(q["AE"])
            + "}{"
            + bracket(q["A1E"])
            + r"}\cdot "
            + bracket(q["a"])
            + "="
            + value(q["AK"])
        )
        + "<p>В прямоугольном треугольнике AKB найдём гипотенузу и высоту AH, вычисляя площадь двумя способами:</p>"
        + line(
            r"BK=\sqrt{AB^2+AK^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["AK"])
            + "^2}="
            + value(q["BK"])
        )
        + line(
            r"AH=\frac{AK\cdot AB}{BK}=\frac{"
            + bracket(q["AK"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{"
            + value(q["BK"])
            + "}="
            + value(q["AH"])
        )
        + "<p>В прямоугольном треугольнике AHE:</p>"
        + line(
            r"\tan\angle AHE=\frac{AE}{AH}=\frac{"
            + bracket(q["AE"])
            + "}{"
            + bracket(q["AH"])
            + "}="
            + value(q["tan"])
        )
    )
    result = parts(proof, quantity)
    if "image_2" in pictures:
        from .prism_opposite_plane_coordinates import render as coordinates

        result += coordinates(m, pictures)
    return result
