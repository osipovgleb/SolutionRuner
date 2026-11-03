"""Keep the parent angle and arc methods, with explicit exact substitutions."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import value
from ..triangles.right.altitude_methods import solution_section


def _central(m):
    d = value(m.given[0])
    return (
        "<p>Пусть центральный и вписанный углы опираются на дугу 2α градусов. Центральный угол равен дуге, на которую он опирается, а вписанный — её половине. Поэтому их величины равны соответственно 2α и α градусов:</p>"
        + line(r"\angle AOB=2\alpha")
        + line(r"\angle ACB=\alpha")
        + "<p>Используем данную разность углов и найдём центральный угол:</p>"
        + line(r"2\alpha-\alpha=" + d + r"^{\circ}")
        + line(r"\alpha=" + d + r"^{\circ}")
        + line(
            r"\angle AOB=2\alpha=2\cdot "
            + d
            + r"^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )


def _difference(m):
    d = value(m.given[0])
    result = (
        "<p>Пусть вписанный угол равен x. Центральный угол, опирающийся на ту же дугу, вдвое больше вписанного. Запишем данную разность углов:</p>"
        + line(r"\beta=2x")
        + line("2x-x=" + d + r"^{\circ}")
        + line("x=" + d + r"^{\circ}")
    )
    if m.central:
        result += (
            "<p>Требуется центральный угол, поэтому удвоим найденный вписанный:</p>"
            + line(
                r"\beta=2x=2\cdot " + d + r"^{\circ}=" + value(m.answer) + r"^{\circ}"
            )
        )
    return result


def _fraction(m):
    fraction = m.given[0] / 100 if m.percent else m.given[0]
    prefix = (
        "<p>Переведём долю окружности из процентов в дробь:</p>"
        + line(
            "f="
            + value(m.given[0])
            + r"\% =\frac{"
            + value(m.given[0])
            + "}{100}="
            + value(fraction)
        )
        if m.percent
        else ""
    )
    target = r"\angle ABC" if m.named else r"\alpha"
    return prefix + (
        "<p>Вписанный угол равен половине дуги, на которую опирается. Поэтому его величина составляет половину данной доли полного угла:</p>"
        + line(r"f=" + value(fraction))
        + line(
            r"\frac{f}{2}=\frac{1}{2}\cdot "
            + value(fraction)
            + "="
            + value(fraction / 2)
        )
        + "<p>Полный угол равен 360°. Переведём найденную долю в градусы:</p>"
        + line(target + r"=360^{\circ}\cdot\frac{f}{2}")
        + line(
            target
            + r"=360^{\circ}\cdot "
            + value(fraction / 2)
            + "="
            + value(m.answer)
            + r"^{\circ}"
        )
    )


def _arcs(m):
    a, b = map(value, m.given)
    remaining = value(360 - sum(m.given))
    return (
        "<p>Дуги AC, BC и AB, каждая из которых не содержит третьей вершины, составляют всю окружность. Найдём градусную меру дуги AB, не содержащей C:</p>"
        + line(
            r"\overset{\frown}{AB}=360^{\circ}-\overset{\frown}{AC}-\overset{\frown}{BC}"
        )
        + line(
            r"\overset{\frown}{AB}=360^{\circ}-" + a + r"^{\circ}-" + b + r"^{\circ}"
        )
        + line(r"\overset{\frown}{AB}=" + remaining + r"^{\circ}")
        + "<p>Вписанный угол равен половине дуги, на которую он опирается:</p>"
        + line(r"\angle ACB=\frac{1}{2}\overset{\frown}{AB}")
        + line(
            r"\angle ACB=\frac{1}{2}\cdot "
            + remaining
            + r"^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )


def _diameters(m):
    given = m.given[0]
    central = m.answer if m.mode == "diameters_central" else given
    inscribed = given if m.mode == "diameters_central" else m.answer
    common = "<p>Вписанный угол равен половине центрального угла, опирающегося на ту же дугу. Углы AOB и AOD смежные, поскольку BD — диаметр:</p>"
    if m.mode == "diameters_central":
        return common + (
            line(r"\angle AOB=2\angle ACB")
            + line(
                r"\angle AOB=2\cdot "
                + value(inscribed)
                + r"^{\circ}="
                + value(2 * inscribed)
                + r"^{\circ}"
            )
            + line(r"\angle AOD=180^{\circ}-\angle AOB")
            + line(
                r"\angle AOD=180^{\circ}-"
                + value(2 * inscribed)
                + r"^{\circ}="
                + value(central)
                + r"^{\circ}"
            )
        )
    return common + (
        line(r"\angle AOB=180^{\circ}-\angle AOD")
        + line(
            r"\angle AOB=180^{\circ}-"
            + value(central)
            + r"^{\circ}="
            + value(2 * inscribed)
            + r"^{\circ}"
        )
        + line(r"\angle ACB=\frac{1}{2}\angle AOB")
        + line(
            r"\angle ACB=\frac{1}{2}\cdot "
            + value(2 * inscribed)
            + r"^{\circ}="
            + value(inscribed)
            + r"^{\circ}"
        )
    )


def _diameters_alternative(m):
    return (
        "<p>Дуга BAD стягивается диаметром BD, поэтому равна 180°. Центральный угол AOD равен дуге AD, на которую он опирается. Тогда меньшая дуга AB равна:</p>"
        + line(r"\overset{\frown}{BAD}=180^{\circ}")
        + line(r"\overset{\frown}{AD}=\angle AOD=" + value(m.given[0]) + r"^{\circ}")
        + line(
            r"\overset{\frown}{AB}=180^{\circ}-"
            + value(m.given[0])
            + r"^{\circ}="
            + value(2 * m.answer)
            + r"^{\circ}"
        )
        + "<p>Вписанный угол ACB равен половине дуги AB, на которую опирается:</p>"
        + line(r"\angle ACB=\frac{1}{2}\overset{\frown}{AB}")
        + line(
            r"\angle ACB=\frac{1}{2}\cdot "
            + value(2 * m.answer)
            + r"^{\circ}="
            + value(m.answer)
            + r"^{\circ}"
        )
    )


def _secants(m):
    external, arc = m.given
    return (
        "<p>Пусть искомый вписанный угол DAE равен x, тогда дуга DE, на которую он опирается, равна 2x. Угол между секущими CB и CA равен полуразности дуг AB и DE:</p>"
        + line(r"\overset{\frown}{DE}=2x")
        + line(r"\angle ACB=\frac{\overset{\frown}{AB}-\overset{\frown}{DE}}{2}")
        + line(r"\frac{" + value(arc) + "-2x}{2}=" + value(external))
        + "<p>Разделим каждое слагаемое числителя на 2 и выразим x:</p>"
        + line(value(arc / 2) + "-x=" + value(external))
        + line("x=" + value(arc / 2) + "-" + value(external) + "=" + value(m.answer))
    )


def render(m, pictures):
    method = {
        "central_difference": _central,
        "difference_equation": _difference,
        "fraction": _fraction,
        "two_arcs": _arcs,
        "diameters_central": _diameters,
        "diameters_inscribed": _diameters,
        "secants": _secants,
    }[m.mode]
    result = solution_section("Решение", pictures.get("reference", "") + method(m))
    if m.mode == "diameters_inscribed":
        result += solution_section("Приведем другое решение", _diameters_alternative(m))
    return result
