"""Equal trapezoidal bases precede the parent's linear-angle construction."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts


def _volumes(m):
    q = m.q
    return (
        "<p>Плоскость ADB₁ делит призму на пирамиды B₁AA₁C₁D и ABCDB₁. У первой вершина B₁ и основание AA₁C₁D в грани ACC₁A₁; у второй вершина A и основание BCDB₁ в грани BCC₁B₁. Их основания — равные прямоугольные трапеции: параллельные стороны равны боковому ребру и его половине, а расстояние между ними равно стороне основания призмы.</p>"
        + line(
            r"CD=DC_1=\frac{CC_1}{2}=\frac{"
            + value(q["height"])
            + "}{2}="
            + value(q["half_height"])
        )
        + line(r"S_{AA_1C_1D}=S_{BCDB_1}=\frac{AA_1+DC_1}{2}\cdot AC")
        + line(
            r"S_{AA_1C_1D}=\frac{"
            + value(q["height"])
            + "+"
            + bracket(q["half_height"])
            + r"}{2}\cdot "
            + bracket(q["a"])
            + "="
            + value(q["trapezoid_area"])
        )
        + "<p>Высоты пирамид — расстояния от B₁ и A до этих боковых граней. Обе равны высоте равностороннего треугольника ABC. Обозначим эту общую высоту через h₀:</p>"
        + line(
            r"h_0=\frac{AB\sqrt3}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt3}{2}="
            + value(q["base_height"])
        )
        + line(
            r"V_{B_1AA_1C_1D}=V_{ABCDB_1}=\frac{1}{3}S_{AA_1C_1D}h_0="
            + value(q["pyramid_volume"])
        )
        + "<p>Равные объёмы этих двух пирамид в сумме составляют объём призмы. Следовательно, плоскость делит её объём пополам.</p>"
    )


def _angle(m):
    q = m.q
    return (
        "<p>Прямая B₁D пересекает продолжение BC за точку C в точке K. Плоскости ABC и ADB₁ пересекаются по AK. Опустим из D перпендикуляр DH на AK. Его проекция CH также перпендикулярна AK по теореме о трёх перпендикулярах. Поэтому угол CHD — линейный угол искомого двугранного угла.</p>"
        + "<p>Прямоугольные треугольники B₁C₁D и KCD равны по катету C₁D = CD и прилежащему острому углу: эти углы вертикальные. Отсюда:</p>"
        + line(r"CK=B_1C_1=AC=" + value(q["a"]))
        + "<p>Треугольник ACK равнобедренный, его угол ACK равен 120°. Высота CH является и биссектрисой этого угла, поэтому:</p>"
        + line(
            r"CH=AC\cos60^\circ="
            + bracket(q["a"])
            + r"\cdot\frac{1}{2}="
            + value(q["CH"])
        )
        + "<p>В прямоугольном треугольнике CDH с прямым углом C:</p>"
        + line(
            r"\tan\angle CHD=\frac{CD}{CH}=\frac{"
            + bracket(q["half_height"])
            + "}{"
            + bracket(q["CH"])
            + "}="
            + value(q["tan"])
        )
    )


def render(m, pictures):
    return parts(pictures.get("image_1", "") + _volumes(m), _angle(m))
