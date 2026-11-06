"""Both parent methods: two cosine laws followed by a vertical midline."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def render(m, pictures):
    q = m.q
    first = (
        pictures.get("image_1", "")
        + "<p>Параллельные плоскости KQP и ABC пересекаются с гранью ASB по параллельным KQ и AB, а с гранью ASC — по параллельным KP и AC. По теореме Фалеса Q и P — середины SB и SC. Значит, PQ — средняя линия треугольника SBC. Она пересекает медиану SN в середине R.</p>"
    )
    second = (
        "<p>Плоскость SAN — плоскость симметрии пирамиды, поэтому AP = AQ. В равнобедренных треугольниках SBC и APQ медианы SN и AR перпендикулярны основаниям BC и PQ; AN также перпендикулярна BC. Линия пересечения плоскостей ABC и APQ проходит через A параллельно PQ. Следовательно, угол RAN — линейный угол искомого двугранного угла.</p>"
        + line(r"AN=\frac{AB\sqrt3}{2}=" + value(q["AN"]))
        + line(r"HN=\frac{AN}{3}=\frac{" + bracket(q["AN"]) + "}{3}=" + value(q["HN"]))
        + line(
            r"SN=\sqrt{SH^2+HN^2}=\sqrt{"
            + bracket(q["H"])
            + "^2+"
            + bracket(q["HN"])
            + "^2}="
            + value(q["SN"])
        )
        + line(r"RN=\frac{SN}{2}=\frac{" + bracket(q["SN"]) + "}{2}=" + value(q["RN"]))
        + line(
            r"\cos\angle HNS=\frac{HN}{SN}=\frac{"
            + bracket(q["HN"])
            + "}{"
            + bracket(q["SN"])
            + "}"
        )
        + "<p>Углы ANR и HNS равны. По теореме косинусов в треугольнике ANR:</p>"
        + line(r"AR^2=AN^2+RN^2-2AN\cdot RN\cos\angle HNS")
        + line(
            r"AR^2="
            + bracket(q["AN"])
            + "^2+"
            + bracket(q["RN"])
            + r"^2-2\cdot "
            + bracket(q["AN"])
            + r"\cdot "
            + bracket(q["RN"])
            + r"\cdot\frac{"
            + bracket(q["HN"])
            + "}{"
            + bracket(q["SN"])
            + "}="
            + value(q["AR"] ** 2)
        )
        + "<p>Ещё раз применим теорему косинусов, теперь для угла RAN:</p>"
        + line(r"\cos\angle RAN=\frac{AR^2+AN^2-RN^2}{2AR\cdot AN}")
        + line(
            r"\cos\angle RAN=\frac{"
            + bracket(q["AR"])
            + "^2+"
            + bracket(q["AN"])
            + "^2-"
            + bracket(q["RN"])
            + r"^2}{2\cdot "
            + bracket(q["AR"])
            + r"\cdot "
            + bracket(q["AN"])
            + "}="
            + value(q["cosine"])
        )
    )
    other = (
        "<p><b>Другой способ.</b> Проведём через R прямую RT ∥ SH до пересечения с AN. В треугольнике SHN отрезок RT — средняя линия:</p>"
        + line(r"RT=\frac{SH}{2}=\frac{" + bracket(q["H"]) + "}{2}=" + value(q["RT"]))
        + line(r"AT=AH+HT=AH+\frac{HN}{2}=AN-\frac{HN}{2}")
        + line(
            r"AT="
            + value(q["AN"])
            + r"-\frac{"
            + bracket(q["HN"])
            + "}{2}="
            + value(q["AT"])
        )
        + "<p>В прямоугольном треугольнике ART:</p>"
        + line(
            r"\tan\angle RAN=\frac{RT}{AT}=\frac{"
            + bracket(q["RT"])
            + "}{"
            + bracket(q["AT"])
            + "}="
            + value(q["tan"])
        )
    )
    return parts(first, second) + other
