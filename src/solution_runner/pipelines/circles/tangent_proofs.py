"""Preserve the reviewed chord and tangent methods and their original order."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section

ARC = r"\overset{\frown}{AB}"
FAR = r"\overset{\frown}{AD}"


def _chord_thirty(m):
    radius = value(m.given[1])
    return (
        "<p>Вписанный угол ABC равен 30°. Центральный угол AOC, опирающийся на ту же хорду, вдвое больше:</p>"
        + line(r"\angle AOC=2\angle ABC=2\cdot30^{\circ}=60^{\circ}")
        + "<p>Радиусы AO и OC равны. Поэтому углы при основании AC равны, и каждый из них составляет:</p>"
        + line("AO=OC=R=" + radius)
        + line(r"\angle OAC=\angle OCA=\frac{180^{\circ}-60^{\circ}}{2}=60^{\circ}")
        + "<p>Все углы треугольника AOC равны 60°, значит, он равносторонний. Искомая хорда равна радиусу:</p>"
        + line("AC=AO=R")
        + line("AC=" + value(m.answer))
    )


def _chord_obtuse(m):
    radius = m.given[1]
    first = (
        "<p>Применим теорему синусов к треугольнику ABC. Отношение стороны к синусу противолежащего угла равно диаметру описанной окружности:</p>"
        + line(r"\frac{AC}{\sin\angle ABC}=2R")
        + line(r"AC=2R\sin\angle ABC")
        + line(r"\sin120^{\circ}=\frac{\sqrt{3}}{2}")
        + line(r"AC=2\cdot " + bracket(radius) + r"\cdot\frac{\sqrt{3}}{2}")
        + line(r"AC=" + bracket(radius) + r"\cdot\sqrt{3}=" + value(m.answer))
    )
    second = (
        "<p>Вписанный угол дополняет половину меньшего центрального угла, опирающегося на ту же хорду, до 180°. Найдём центральный угол:</p>"
        + line(r"\angle AOC=2(180^{\circ}-\angle ABC)")
        + line(r"\angle AOC=2(180^{\circ}-120^{\circ})=120^{\circ}")
        + "<p>Радиусы AO и OC равны R. Применим теорему косинусов к треугольнику AOC:</p>"
        + line("AO=OC=R=" + value(radius))
        + line(r"AC^2=AO^2+OC^2-2AO\cdot OC\cos\angle AOC")
        + line(r"\cos120^{\circ}=-\frac{1}{2}")
        + line(r"AC^2=2R^2+R^2=3R^2")
        + line(
            r"AC=\sqrt{3R^2}=\sqrt{3}\cdot " + bracket(radius) + "=" + value(m.answer)
        )
    )
    return first, second


def _ratio(m):
    small, large = sorted(m.given)
    unit = 360 / (small + large)
    return (
        "<p>Из точки C хорда AB видна под вписанным углом ACB. Пусть меньшая дуга равна "
        + value(small)
        + "x, а большая — "
        + value(large)
        + "x. Сумма дуг составляет 360°:</p>"
        + line(value(large) + "x+" + value(small) + r"x=360^{\circ}")
        + line(value(large + small) + r"x=360^{\circ}")
        + line(
            r"x=\frac{360^{\circ}}{"
            + value(large + small)
            + "}="
            + value(unit)
            + r"^{\circ}"
        )
        + "<p>Точка C принадлежит меньшей дуге, поэтому вписанный угол опирается на большую. Найдём её величину и разделим пополам:</p>"
        + line(
            r"\beta="
            + value(large)
            + "x="
            + value(large)
            + r"\cdot "
            + bracket(unit)
            + r"^{\circ}="
            + value(large * unit)
            + r"^{\circ}"
        )
        + line(
            r"\angle ACB=\frac{\beta}{2}=\frac{"
            + value(large * unit)
            + "}{2}^{\\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )


def _tangent_chord(m):
    return (
        "<p>Угол между касательной и хордой равен половине дуги, заключённой между его сторонами. Обозначим градусную меру этой дуги через θ:</p>"
        + line(r"\theta=" + value(m.given[0]) + r"^{\circ}")
        + line(r"\angle ABC=\frac{\theta}{2}")
        + line(r"\angle ABC=\frac{" + value(m.given[0]) + "}{2}^{\\circ}")
        + line(r"\angle ABC=" + value(m.answer) + r"^{\circ}")
    )


def _central(m):
    return (
        "<p>Угол между касательной AC и хордой AB, проведённой в точку касания A, равен половине заключённой между ними дуги. Найдём меньшую дугу AB:</p>"
        + line(ARC + r"=2\angle CAB")
        + line(ARC + r"=2\cdot " + value(m.given[0]) + r"^{\circ}")
        + line(ARC + "=" + value(m.answer) + r"^{\circ}")
        + "<p>Центральный угол измеряется дугой, на которую он опирается:</p>"
        + line(r"\angle AOB=" + ARC)
        + line(r"\angle AOB=" + value(m.answer) + r"^{\circ}")
    )


def _two_angle(m):
    half = m.given[0] / 2
    return (
        "<p>Угол между касательной и хордой равен половине заключённой между ними дуги. Найдём углы при основании AB треугольника ABC:</p>"
        + line(r"\angle CAB=\angle CBA=\frac{1}{2}" + ARC)
        + line(
            r"\angle CAB=\angle CBA=\frac{"
            + value(m.given[0])
            + "}{2}^{\\circ}="
            + value(half)
            + r"^{\circ}"
        )
        + "<p>Сумма углов треугольника равна 180°. Поэтому:</p>"
        + line(r"\angle ACB=180^{\circ}-(\angle CAB+\angle CBA)")
        + line(r"\angle ACB=180^{\circ}-" + value(m.given[0]) + r"^{\circ}")
        + line(r"\angle ACB=" + value(m.answer) + r"^{\circ}")
    )


def _two_arc(m):
    a, half = m.given[0], m.answer / 2
    first = (
        "<p>Треугольник ABC равнобедренный: отрезки касательных, проведённых к окружности из одной точки, равны. Найдём угол при основании:</p>"
        + line("CA=CB")
        + line(r"\angle BAC=\frac{180^{\circ}-\angle ACB}{2}")
        + line(
            r"\angle BAC=\frac{180^{\circ}-"
            + value(a)
            + r"^{\circ}}{2}="
            + value(half)
            + r"^{\circ}"
        )
        + "<p>Угол между касательной и хордой равен половине заключённой между ними дуги, поэтому:</p>"
        + line(ARC + r"=2\angle BAC")
        + line(
            ARC
            + r"=2\cdot "
            + bracket(half)
            + r"^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )
    second = (
        "<p>Пусть искомая градусная мера меньшей дуги AB равна x. Тогда большая дуга равна 360°−x. Угол между двумя касательными из одной точки равен полуразности высекаемых ими дуг:</p>"
        + line(r"\frac{(360^{\circ}-x)-x}{2}=" + value(a) + r"^{\circ}")
        + line(r"360^{\circ}-2x=" + value(2 * a) + r"^{\circ}")
        + line(
            r"2x=360^{\circ}-"
            + value(2 * a)
            + r"^{\circ}="
            + value(2 * m.answer)
            + r"^{\circ}"
        )
        + line(
            r"x=\frac{"
            + value(2 * m.answer)
            + "}{2}^{\\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )
    third = (
        "<p>Радиус, проведённый в точку касания, перпендикулярен касательной. Поэтому углы OAC и OBC прямые. Используем сумму углов четырёхугольника OACB:</p>"
        + line(r"\angle OAC=\angle OBC=90^{\circ}")
        + line(r"\angle AOB=360^{\circ}-\angle ACB-\angle OAC-\angle OBC")
        + line(
            r"\angle AOB=360^{\circ}-"
            + value(a)
            + r"^{\circ}-90^{\circ}-90^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
        + "<p>Угол AOB центральный и равен дуге, на которую опирается:</p>"
        + line(ARC + r"=\angle AOB=" + value(m.answer) + r"^{\circ}")
    )
    return first, second, third


def _near(m):
    arc = m.given[0] if m.mode == "near_angle" else m.answer
    angle = m.answer if m.mode == "near_angle" else m.given[0]
    result = (
        "<p>Касательная CA перпендикулярна радиусу OA. Треугольник AOC прямоугольный, а центральный угол AOC равен дуге AB:</p>"
        + line(r"\angle OAC=90^{\circ}")
    )
    if m.mode == "near_angle":
        return result + (
            line(r"\angle AOC=" + ARC + "=" + value(arc) + r"^{\circ}")
            + "<p>Найдём второй острый угол прямоугольного треугольника:</p>"
            + line(r"\angle ACO=90^{\circ}-\angle AOC")
            + line(
                r"\angle ACO=90^{\circ}-"
                + value(arc)
                + r"^{\circ}="
                + value(angle)
                + r"^{\circ}"
            )
        )
    return result + (
        line(r"\angle AOC=90^{\circ}-\angle ACO")
        + line(
            r"\angle AOC=90^{\circ}-"
            + value(angle)
            + r"^{\circ}="
            + value(arc)
            + r"^{\circ}"
        )
        + "<p>Центральный угол равен дуге, на которую опирается:</p>"
        + line(ARC + r"=\angle AOC=" + value(arc) + r"^{\circ}")
    )


def _far_angle(m):
    arc, near = m.given[0], 180 - m.given[0]
    first = (
        "<p>Хорда DB — диаметр, поэтому дуга AB, не содержащая D, дополняет данную дугу AD до 180°. Найдём её и соответствующий центральный угол:</p>"
        + line(ARC + r"=180^{\circ}-" + FAR)
        + line(
            ARC
            + r"=180^{\circ}-"
            + value(arc)
            + r"^{\circ}="
            + value(near)
            + r"^{\circ}"
        )
        + line(r"\angle AOB=" + ARC)
        + "<p>Радиус OA перпендикулярен касательной CA. В прямоугольном треугольнике AOC получаем:</p>"
        + line(r"\angle ACO=90^{\circ}-\angle AOB")
        + line(
            r"\angle ACO=90^{\circ}-"
            + value(near)
            + r"^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )
    second = (
        "<p>Центральный угол AOD равен дуге AD. Он является внешним углом треугольника AOC, поэтому равен сумме двух внутренних углов, не смежных с ним:</p>"
        + line(r"\angle AOD=" + FAR + "=" + value(arc) + r"^{\circ}")
        + line(r"\angle AOD=\angle OAC+\angle ACO")
        + "<p>Угол OAC равен 90° как угол между касательной и радиусом в точке касания. Выразим искомый угол:</p>"
        + line(r"\angle OAC=90^{\circ}")
        + line(r"\angle ACO=\angle AOD-\angle OAC")
        + line(
            r"\angle ACO="
            + value(arc)
            + r"^{\circ}-90^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )
    return first, second


def _far_arc(m):
    angle = m.given[0]
    first = (
        "<p>Хорда DB — диаметр. Обозначим искомую дугу AD через x; тогда дуга AB равна 180°−x. Угол между секущей и касательной равен полуразности высекаемых ими дуг:</p>"
        + line(r"\frac{x-(180^{\circ}-x)}{2}=" + value(angle) + r"^{\circ}")
        + line(r"2x-180^{\circ}=" + value(2 * angle) + r"^{\circ}")
        + line(
            r"2x=180^{\circ}+"
            + value(2 * angle)
            + r"^{\circ}="
            + value(2 * m.answer)
            + r"^{\circ}"
        )
        + line(
            r"x=\frac{"
            + value(2 * m.answer)
            + "}{2}^{\\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )
    second = (
        "<p>Касательная CA перпендикулярна радиусу OA. В прямоугольном треугольнике AOC найдём центральный угол AOB:</p>"
        + line(r"\angle AOB=90^{\circ}-\angle ACO")
        + line(
            r"\angle AOB=90^{\circ}-"
            + value(angle)
            + r"^{\circ}="
            + value(90 - angle)
            + r"^{\circ}"
        )
        + "<p>Центральный угол DOA равен дуге AD и дополняет угол AOB до 180°:</p>"
        + line(FAR + r"=\angle DOA=180^{\circ}-\angle AOB")
        + line(
            FAR
            + r"=180^{\circ}-"
            + value(90 - angle)
            + r"^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )
    return first, second


def render(m, pictures):
    if m.mode == "chord_obtuse":
        first, second = _chord_obtuse(m)
        return solution_section(
            "Решение", pictures["detail"] + first
        ) + solution_section("Приведём другое решение", second)
    if m.mode == "two_tangents_arc":
        first, second, third = _two_arc(m)
        return (
            solution_section("Решение", first)
            + solution_section("Приведем другое решение", second)
            + solution_section("Альтернативное решение.", third)
        )
    if m.mode in {"far_angle", "far_arc"}:
        first, second = (_far_angle if m.mode == "far_angle" else _far_arc)(m)
        return solution_section("Решение", first) + solution_section(
            "Альтернативное решение."
            if m.mode == "far_angle"
            else "Приведём другое решение",
            second,
        )
    method = {
        "chord_thirty": _chord_thirty,
        "arc_ratio": _ratio,
        "tangent_chord": _tangent_chord,
        "central_from_tangent": _central,
        "two_tangents_angle": _two_angle,
        "near_angle": _near,
        "near_arc": _near,
    }[m.mode]
    body = method(m)
    detail = pictures.get("detail", "")
    return solution_section(
        "Решение", body + detail if m.mode == "central_from_tangent" else detail + body
    )
