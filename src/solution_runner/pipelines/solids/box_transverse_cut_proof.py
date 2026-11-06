"""Parallel-face similarity and the parent's projection construction for either face."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _incidence(m, pictures):
    q = m.q
    text = (
        pictures.get("image_1", "") + "<p>Сначала найдём отрезки на боковых рёбрах:</p>"
    )
    text += line(
        r"A_1E=\frac{"
        + value(q["p"])
        + "}{"
        + value(q["p"] + q["q"])
        + r"}AA_1=\frac{"
        + value(q["p"])
        + "}{"
        + value(q["p"] + q["q"])
        + r"}\cdot "
        + bracket(q["height"])
        + "="
        + value(q["d"])
    )
    text += line(
        r"B_1T=\frac{B_1C_1}{2}=\frac{" + value(q["b"]) + "}{2}=" + value(q["B1T"])
    )
    if m.mode.endswith("ratio_angle"):
        return (
            text
            + "<p>Плоскость сечения пересекает параллельные грани AA₁D₁D и BB₁C₁C по параллельным прямым ED₁ и QT. Поэтому треугольники EA₁D₁ и QB₁T подобны:</p>"
            + line(r"\frac{QB_1}{EA_1}=\frac{B_1T}{A_1D_1}=\frac12")
            + line(
                r"QB_1=\frac{EA_1}{2}=\frac{"
                + value(q["d"])
                + "}{2}="
                + value(q["B1F"])
            )
            + line(
                r"QB=BB_1-QB_1="
                + value(q["height"])
                + "-"
                + bracket(q["B1F"])
                + "="
                + value(q["FB"])
            )
            + line(
                r"\frac{B_1Q}{QB}=\frac{"
                + value(q["B1F"])
                + "}{"
                + value(q["FB"])
                + "}="
                + value(q["ratio"])
            )
            + "<p>Отношение указано от вершины B₁.</p>"
        )
    return (
        text
        + line(
            r"B_1F=\frac{"
            + value(q["fp"])
            + "}{"
            + value(q["fp"] + q["fq"])
            + r"}BB_1=\frac{"
            + value(q["fp"])
            + "}{"
            + value(q["fp"] + q["fq"])
            + r"}\cdot "
            + bracket(q["height"])
            + "="
            + value(q["B1F"])
        )
        + "<p>В грани AA₁D₁D проведём через E прямую, параллельную FT, до пересечения с A₁D₁ в U. Параллельность граней даёт подобие прямоугольных треугольников EA₁U и FB₁T:</p>"
        + line(
            r"A_1U=\frac{EA_1\cdot B_1T}{FB_1}=\frac{"
            + bracket(q["d"])
            + r"\cdot "
            + bracket(q["B1T"])
            + "}{"
            + value(q["B1F"])
            + "}="
            + value(q["b"])
            + r"=A_1D_1"
        )
        + "<p>Значит, U совпадает с D₁. Прямая ED₁ параллельна FT, поэтому D₁ лежит в плоскости EFT.</p>"
    )


def _first_face(m):
    q = m.q
    return (
        "<p>Прямая A₁D₁ перпендикулярна плоскости AA₁B₁. Опустим из A₁ перпендикуляр A₁H на EQ — линию пересечения плоскостей. По теореме о трёх перпендикулярах D₁H ⟂ EQ, поэтому ∠A₁HD₁ — линейный угол искомого двугранного угла.</p>"
        + "<p>В трапеции EA₁B₁Q опустим QL ⟂ EA₁. Тогда QL = AB, а EL = QB₁. Дважды выразим площадь треугольника EQA₁:</p>"
        + line(
            r"EQ=\sqrt{QL^2+EL^2}=\sqrt{"
            + bracket(q["a"])
            + "^2+"
            + bracket(q["B1F"])
            + "^2}="
            + value(q["EQ"])
        )
        + line(r"\frac{A_1E\cdot QL}{2}=\frac{EQ\cdot A_1H}{2}")
        + line(
            r"A_1H=\frac{A_1E\cdot QL}{EQ}=\frac{"
            + bracket(q["d"])
            + r"\cdot "
            + bracket(q["a"])
            + "}{"
            + value(q["EQ"])
            + "}="
            + value(q["A1H"])
        )
        + "<p>Треугольник A₁HD₁ прямоугольный при A₁, следовательно:</p>"
        + line(
            r"\tan\angle A_1HD_1=\frac{A_1D_1}{A_1H}=\frac{"
            + bracket(q["b"])
            + "}{"
            + bracket(q["A1H"])
            + "}="
            + value(q["tan"])
        )
    )


def _second_face(m):
    q = m.q
    return (
        "<p>Теперь линией пересечения плоскостей служит FT. В грани BB₁C₁C опустим перпендикуляр B₁K к FT, а в плоскости EFT через K проведём перпендикуляр к FT до пересечения с ED₁ в L. Для выбора острого линейного угла обозначим проекцию L на грань BB₁C₁C через X. Тогда LX ∥ AB и LX = AB. По теореме о трёх перпендикулярах KX ⟂ FT.</p>"
        + "<p>Проекции E и D₁ на эту грань лежат соответственно на продолжении B₁F и в C₁. Гомотетия с центром B₁ и коэффициентом 2 переводит F и T в эти две проекции, а перпендикуляр B₁K — в B₁X. Следовательно, X лежит на продолжении B₁K за K и KX = B₁K. Угол LKX — острый линейный угол между плоскостями; угол B₁KL смежный с ним.</p>"
        + "<p>Из площади прямоугольного треугольника FB₁T найдём высоту B₁K:</p>"
        + line(
            r"FT=\sqrt{B_1F^2+B_1T^2}=\sqrt{"
            + bracket(q["B1F"])
            + "^2+"
            + bracket(q["B1T"])
            + "^2}="
            + value(q["FT"])
        )
        + line(
            r"B_1K=\frac{B_1F\cdot B_1T}{FT}=\frac{"
            + bracket(q["B1F"])
            + r"\cdot "
            + bracket(q["B1T"])
            + "}{"
            + value(q["FT"])
            + "}="
            + value(q["B1K"])
        )
        + "<p>Треугольник LXK прямоугольный при X. Используем ту же формулу тангенса линейного угла, что и для другой грани:</p>"
        + line(
            r"\tan\angle LKX=\frac{LX}{KX}=\frac{AB}{B_1K}=\frac{"
            + bracket(q["a"])
            + "}{"
            + bracket(q["B1K"])
            + "}="
            + value(q["tan"])
        )
        + line(
            r"\cos\angle LKX=\frac{1}{\sqrt{1+\tan^2\angle LKX}}=\frac{1}{\sqrt{1+"
            + bracket(q["tan"])
            + "^2}}="
            + value(q["cos"])
        )
    )


def render(m, pictures):
    return parts(
        _incidence(m, pictures),
        _first_face(m) if m.mode.endswith("ratio_angle") else _second_face(m),
    )
