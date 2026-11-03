"""Preserve the parent's altitude-triangle methods and adapt exact angle data."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from ..parallelogram.rectangle_proofs import bracket, value


def _area_rows(m, height):
    return line(r"S_{ABCD}=\frac{AD+BC}{2}\cdot " + height) + line(
        r"S_{ABCD}=\frac{"
        + value(m.large + m.small)
        + r"}{2}\cdot "
        + bracket(m.height)
        + "="
        + value(m.area)
    )


def _right_area(m):
    angle = m.given[2]
    result = (
        "<p>Проведём высоту CH. Треугольник CHD прямоугольный; его угол при вершине D равен данному углу между большей боковой стороной и основанием:</p>"
        + line(r"\angle CDA=" + value(angle) + r"^{\circ}")
        + line("HD=AD-BC")
        + line(
            "HD=" + value(m.large) + "-" + value(m.small) + "=" + value(m.projection)
        )
    )
    if angle == 45:
        result += (
            "<p>Второй острый угол треугольника также равен 45°, поэтому треугольник равнобедренный:</p>"
            + line("CH=HD")
            + line("CH=" + value(m.height))
        )
    else:
        result += (
            "<p>По определению тангенса выразим высоту через прилежащий катет HD:</p>"
            + line(r"\tg\angle CDA=\frac{CH}{HD}")
            + line(r"CH=HD\tg\angle CDA")
            + line(
                "CH="
                + value(m.projection)
                + r"\cdot\tg"
                + value(angle)
                + r"^{\circ}="
                + value(m.height)
            )
        )
    return (
        result
        + "<p>Подставим найденную высоту в формулу площади трапеции:</p>"
        + _area_rows(m, "CH")
    )


def _right_angle(m):
    result = (
        "<p>Найдём длину высоты CH из формулы площади трапеции:</p>"
        + line(r"S_{ABCD}=\frac{AD+BC}{2}\cdot CH")
        + line(r"CH=\frac{2S_{ABCD}}{AD+BC}")
        + line(
            r"CH=\frac{2\cdot "
            + value(m.area)
            + "}{"
            + value(m.large + m.small)
            + "}="
            + value(m.height)
        )
        + line("HD=AD-BC=" + value(m.projection))
    )
    if m.height == m.projection:
        return result + (
            "<p>В прямоугольном треугольнике CHD катеты равны. Значит, он равнобедренный, а его острые углы равны:</p>"
            + line("CH=HD")
            + line(r"\angle CDH=\angle HCD")
            + line(r"2\angle CDH=90^{\circ}")
            + line(r"\angle CDA=\angle CDH=\frac{90^{\circ}}{2}=45^{\circ}")
        )
    return result + (
        "<p>Катеты не равны. По определению тангенса найдём острый угол при D; значение арктангенса переводим из радиан в градусы:</p>"
        + line(r"\tg\angle CDA=\frac{CH}{HD}")
        + line(r"\tg\angle CDA=" + value(m.tangent))
        + line(
            r"\angle CDA=\frac{180^{\circ}}{\pi}\arctan\left("
            + value(m.tangent)
            + r"\right)="
            + value(m.angle)
            + r"^{\circ}"
        )
    )


def _side_area(m):
    given_angle = m.given[3]
    result = "<p>Углы трапеции, прилежащие к одной боковой стороне, в сумме дают 180°. Найдём острый угол при этой стороне:</p>"
    result += (
        line(
            r"\angle BAD=180^{\circ}-"
            + value(given_angle)
            + r"^{\circ}="
            + value(m.angle)
            + r"^{\circ}"
        )
        if given_angle > 90
        else line(r"\angle BAD=" + value(given_angle) + r"^{\circ}")
    )
    return result + (
        "<p>Найдём высоту BH из прямоугольного треугольника ABH по определению синуса:</p>"
        + line(r"BH=AB\sin\angle BAD")
        + line("AB=" + value(m.leg))
        + line(r"\sin\angle BAD=" + value(m.sine))
        + line(
            "BH=" + value(m.leg) + r"\cdot " + bracket(m.sine) + "=" + value(m.height)
        )
        + "<p>Площадь трапеции равна произведению полусуммы длин оснований на высоту:</p>"
        + _area_rows(m, "BH")
    )


def _side_angle(m):
    result = (
        "<p>Площадь трапеции равна произведению полусуммы длин оснований на высоту. Пусть высота равна h:</p>"
        + line(r"S=\frac{AD+BC}{2}\cdot h")
        + line(r"\frac{" + value(m.large + m.small) + "}{2}h=" + value(m.area))
        + line(
            r"h=\frac{2\cdot "
            + value(m.area)
            + "}{"
            + value(m.large + m.small)
            + "}="
            + value(m.height)
        )
        + "<p>Рассмотрим прямоугольный треугольник ABH: его гипотенуза — данная боковая сторона, а катет BH — высота трапеции:</p>"
        + line("BH=h=" + value(m.height))
        + line("AB=" + value(m.leg))
    )
    if 2 * m.sine == 1:
        result += (
            "<p>Длина катета равна половине гипотенузы. Следовательно, он лежит напротив угла 30°:</p>"
            + line(r"BH=\frac{AB}{2}")
            + line(r"\angle BAD=30^{\circ}")
        )
    else:
        result += (
            "<p>По определению синуса найдём острый угол напротив катета BH; значение арксинуса переводим из радиан в градусы:</p>"
            + line(r"\sin\angle BAD=\frac{BH}{AB}")
            + line(r"\sin\angle BAD=" + value(m.sine))
            + line(
                r"\angle BAD=\frac{180^{\circ}}{\pi}\arcsin\left("
                + value(m.sine)
                + r"\right)="
                + value(m.angle)
                + r"^{\circ}"
            )
        )
    note = (
        "Данные допускают равнобедренную трапецию. На рисунке показана эта конфигурация с равными боковыми сторонами."
        if m.is_isosceles
        else "Заметим, что трапеция не является равнобедренной. Заинтересованные читатели могут самостоятельно найти вторую боковую сторону этой трапеции."
    )
    return result + "<p><b>Примечание.</b></p><p>" + note + "</p>"


def render(m, pictures):
    method = {
        "right_area": _right_area,
        "right_angle": _right_angle,
        "side_area": _side_area,
        "side_angle": _side_angle,
    }[m.mode]
    return solution_section("Решение", pictures["height"] + method(m))
