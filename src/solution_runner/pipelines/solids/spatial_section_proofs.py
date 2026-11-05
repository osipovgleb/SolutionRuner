"""Preserve similarity, bisector and trapezoid constructions in the source order."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .spatial_distance_proofs import parts
from .spatial_metric_proofs import picture


def parallel_height(m, pictures):
    q = m.q
    first = (
        picture(pictures)
        + line("DE=BD-BE=" + value(q["d"]) + "-" + value(q["t"]) + "=" + value(q["DE"]))
        + "<p>Пусть прямая CE пересекает AB в точке M. Треугольники BME и DCE подобны по вертикальным углам при E и углам при параллельных сторонах AB и CD:</p>"
        + line(
            r"\frac{BM}{DC}=\frac{BE}{DE}=\frac{"
            + value(q["t"])
            + "}{"
            + value(q["DE"])
            + "}"
        )
        + line(
            r"BM=DC\cdot\frac{BE}{DE}="
            + bracket(q["a"])
            + r"\cdot\frac{"
            + value(q["t"])
            + "}{"
            + value(q["DE"])
            + "}="
            + value(q["BM"])
        )
        + line(
            "AM=AB-BM=" + value(q["a"]) + "-" + value(q["BM"]) + "=" + value(q["AM"])
        )
        + line("AF=AS-SF=" + value(q["e"]) + "-" + value(q["t"]) + "=" + value(q["AF"]))
        + line(
            r"\frac{AM}{AB}=\frac{"
            + value(q["AM"])
            + "}{"
            + value(q["a"])
            + r"}=\frac{"
            + value(q["AF"])
            + "}{"
            + value(q["e"])
            + r"}=\frac{AF}{AS}"
        )
        + "<p>По обратной теореме Фалеса MF ∥ SB. Прямая MF лежит в плоскости CEF, а SB не лежит в ней, поэтому SB параллельна плоскости CEF.</p>"
    )
    second = (
        "<p>Плоскости CEF и SBD пересекаются по QE. Поскольку SB параллельна CEF, получаем QE ∥ SB. Из подобия треугольников DQE и DSB:</p>"
        + line(
            r"\frac{DQ}{QS}=\frac{DE}{EB}=\frac{"
            + value(q["DE"])
            + "}{"
            + value(q["t"])
            + "}"
        )
        + line(
            r"\frac{DQ}{DS}=\frac{DE}{DB}=\frac{"
            + value(q["DE"])
            + "}{"
            + value(q["d"])
            + "}"
        )
        + "<p>Пусть O — центр прямоугольника ABCD. Все боковые рёбра равны, поэтому SO — высота пирамиды. Найдём её из прямоугольного треугольника SAO:</p>"
        + line(r"AO=\frac{BD}{2}=\frac{" + value(q["d"]) + "}{2}=" + value(q["d"] / 2))
        + line(
            r"SO=\sqrt{SA^2-AO^2}=\sqrt{"
            + bracket(q["e"])
            + "^2-"
            + bracket(q["d"] / 2)
            + "^2}="
            + value(q["H"])
        )
        + "<p>Опустим из Q перпендикуляр QH на основание. Так как Q лежит на SD, точка H лежит на DO. Прямоугольные треугольники DQH и DSO подобны, поэтому:</p>"
        + line(r"QH=\frac{DQ}{DS}\cdot SO")
        + line(
            r"QH=\frac{"
            + value(q["DE"])
            + "}{"
            + value(q["d"])
            + r"}\cdot "
            + bracket(q["H"])
            + "="
            + value(m.answer)
        )
    )
    return parts(first, second)


def bisector(m, pictures):
    q = m.q
    first = (
        "<p>Рассмотрим равнобедренный треугольник ASC. Угол ASC равен углу ASB, поскольку боковые грани правильной пирамиды равны. Найдём углы при основании:</p>"
        + line(r"\angle SAC=\angle SCA=\frac{180^{\circ}-36^{\circ}}{2}=72^{\circ}")
        + "<p>AM — биссектриса, поэтому:</p>"
        + line(r"\angle MAC=\frac{72^{\circ}}{2}=36^{\circ}")
        + line(r"\angle AMC=180^{\circ}-72^{\circ}-36^{\circ}=72^{\circ}")
        + "<p>В треугольнике CAM углы при C и M равны, значит, AC = AM. Основание ABC равностороннее, поэтому AM = AC = AB.</p>"
    )
    second = "<p>Нужное сечение — треугольник AMB. Угол BCM также равен 72°. Треугольники CAM и CBM равны по двум сторонам CA = CB, общей стороне CM и углу между ними. Поэтому BM = AM = AB, то есть треугольник AMB равносторонний.</p>"
    if m.mode == "triangle_bisector_section_area":
        second += (
            "<p>Его сторона совпадает со стороной основания. Подставим данную длину в формулу площади:</p>"
            + line("AB=" + value(q["a"]))
            + line(r"S_{AMB}=\frac{AB^2\sqrt{3}}{4}")
            + line(
                r"S_{AMB}=\frac{"
                + bracket(q["a"])
                + r"^2\sqrt{3}}{4}="
                + value(m.answer)
            )
        )
    else:
        second += (
            "<p>По данной площади сечения составим уравнение для стороны AB:</p>"
            + line(r"\frac{AB^2\sqrt{3}}{4}=" + value(q["section_area"]))
            + line(
                r"AB^2=\frac{4\cdot "
                + bracket(q["section_area"])
                + r"}{\sqrt{3}}="
                + value(q["a"] ** 2)
            )
            + "<p>Длина стороны положительна, поэтому:</p>"
            + line(r"AB=\sqrt{" + value(q["a"] ** 2) + "}=" + value(m.answer))
        )
    return picture(pictures) + parts(first, second)


def _construction(m):
    angle = m.mode == "pyramid_parallel_section_angle"
    l, u, n = ("G", "F", "E") if angle else ("L", "M", "N")
    section = "EFGK" if angle else "KLMN"
    return (
        "<p>В грани ABP через K проведём прямую, параллельную PB. Она пересечёт AB в точке "
        + l
        + ". По теореме о средней линии "
        + l
        + " — середина AB. В основании через "
        + l
        + " проведём прямую, параллельную BC, до пересечения с CD в точке "
        + u
        + "; это середина CD.</p>"
        + "<p>Плоскость K"
        + l
        + u
        + " содержит две пересекающиеся прямые, параллельные PB и BC соответственно. Поэтому она параллельна плоскости BCP и прямым PB и BC. Прямая "
        + l
        + u
        + " параллельна AD. Плоскость сечения пересекает грань APD по прямой через K, параллельной AD. Обозначим её пересечение с PD через "
        + n
        + ". По теореме о средней линии "
        + n
        + " — середина PD.</p>"
        + "<p>Искомое сечение — трапеция "
        + section
        + ".</p>"
    )


def trapezoid_area(m, pictures):
    q = m.q
    second = (
        "<p>KL и MN — средние линии равных треугольников ABP и DCP, а KN — средняя линия треугольника APD. Отрезок LM соединяет середины противоположных сторон квадрата и равен BC. Поэтому сечение — равнобедренная трапеция:</p>"
        + line("LM=AB=" + value(q["a"]))
        + line(
            r"KL=MN=KN=\frac{AB}{2}=\frac{"
            + value(q["a"])
            + "}{2}="
            + value(q["a"] / 2)
        )
        + pictures.get("image_2", "")
        + "<p>Проведём высоту KF трапеции. Из равнобедренности:</p>"
        + line(
            r"LF=\frac{LM-KN}{2}=\frac{"
            + value(q["a"])
            + "-"
            + value(q["a"] / 2)
            + "}{2}="
            + value(q["offset"])
        )
        + line(
            r"KF=\sqrt{KL^2-LF^2}=\sqrt{"
            + bracket(q["a"] / 2)
            + "^2-"
            + bracket(q["offset"])
            + "^2}="
            + value(q["section_height"])
        )
        + "<p>Вычислим площадь трапеции:</p>"
        + line(r"S_{KLMN}=\frac{LM+KN}{2}\cdot KF")
        + line(
            r"S_{KLMN}=\frac{"
            + value(q["a"])
            + "+"
            + value(q["a"] / 2)
            + r"}{2}\cdot "
            + bracket(q["section_height"])
            + "="
            + value(m.answer)
        )
    )
    return picture(pictures) + parts(_construction(m), second)


def trapezoid_angle(m, pictures):
    q = m.q
    second = (
        "<p>Плоскость сечения параллельна BCP. Поэтому её угол с основанием равен углу между BCP и ABC. Пусть N — середина BC, O — основание высоты пирамиды. В равностороннем треугольнике BCP медиана PN является высотой; ON также перпендикулярна BC. Значит, ∠PNO — линейный угол нужного двугранного угла.</p>"
        + line(r"ON=\frac{AB}{2}=\frac{" + value(q["a"]) + "}{2}=" + value(q["a"] / 2))
        + line(
            r"PN=\frac{PB\sqrt{3}}{2}=\frac{"
            + bracket(q["a"])
            + r"\sqrt{3}}{2}="
            + value(q["l"])
        )
        + "<p>В прямоугольном треугольнике PNO:</p>"
        + line(r"\cos\angle PNO=\frac{ON}{PN}")
        + line(
            r"\cos\angle PNO=\frac{"
            + value(q["a"] / 2)
            + "}{"
            + value(q["l"])
            + r"}=\frac{1}{\sqrt{3}}"
        )
        + line(r"\angle PNO=" + value(m.answer))
    )
    return picture(pictures) + parts(_construction(m), second)


def render(m, pictures):
    return {
        "pyramid_parallel_section_height": parallel_height,
        "triangle_bisector_section_edge": bisector,
        "triangle_bisector_section_area": bisector,
        "pyramid_parallel_section_area": trapezoid_area,
        "pyramid_parallel_section_angle": trapezoid_angle,
    }[m.mode](m, pictures)
