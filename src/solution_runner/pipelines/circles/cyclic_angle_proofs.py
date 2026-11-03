"""Preserve cyclic-angle parent methods and exact arc-partition derivations."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section
from .cyclic_angle_model import RULES

MODES = frozenset(RULES.values())


def arc(name):
    return r"\overset{\frown}{" + name + "}"


DEG = r"^{\circ}"


def _opposite(m):
    a = m.given[0]
    first = (
        "<p>Сумма противоположных углов четырёхугольника, вписанного в окружность, равна 180°. Поэтому:</p>"
        + line(r"\angle A+\angle C=180^{\circ}")
        + line(r"\angle C=180^{\circ}-\angle A")
        + line(r"\angle C=180^{\circ}-" + value(a) + DEG)
        + line(r"\angle C=" + value(m.answer) + DEG)
    )
    second = (
        "<p>Угол A вписанный и опирается на дугу BCD, поэтому эта дуга вдвое больше угла:</p>"
        + line(
            arc("BCD")
            + r"=2\angle A=2\cdot "
            + bracket(a)
            + DEG
            + "="
            + value(2 * a)
            + DEG
        )
        + "<p>Дуга BAD дополняет её до полной окружности:</p>"
        + line(arc("BAD") + "=360" + DEG + "-" + arc("BCD"))
        + line(
            arc("BAD")
            + "=360"
            + DEG
            + "-"
            + value(2 * a)
            + DEG
            + "="
            + value(360 - 2 * a)
            + DEG
        )
        + "<p>Вписанный угол C равен половине дуги BAD:</p>"
        + line(r"\angle C=\frac{1}{2}" + arc("BAD"))
        + line(
            r"\angle C=\frac{"
            + value(360 - 2 * a)
            + "}{2}"
            + DEG
            + "="
            + value(m.answer)
            + DEG
        )
    )
    return solution_section("Решение", first) + solution_section(
        "Приведём другое решение.", second
    )


def _partition(m):
    total = sum(m.given)
    unit = 360 / total
    return (
        "<p>Пусть x — общая мера одной части данного отношения. Тогда сумма всех дуг равна полному углу:</p>"
        + line(
            "+".join("x" if v == 1 else bracket(v) + "x" for v in m.given)
            + "=360"
            + DEG
        )
        + line(bracket(total) + "x=360" + DEG)
        + line(r"x=\frac{360}{" + value(total) + "}" + DEG + "=" + value(unit) + DEG)
    )


def _triangle_ratio(m):
    unit = 360 / sum(m.given)
    largest = max(m.given)
    intercepted = largest * unit
    return (
        _partition(m)
        + "<p>Больший угол опирается на большую дугу. Найдём её градусную меру β:</p>"
        + line(
            r"\beta="
            + bracket(largest)
            + "x="
            + bracket(largest)
            + r"\cdot "
            + bracket(unit)
            + DEG
            + "="
            + value(intercepted)
            + DEG
        )
        + "<p>Вписанный угол равен половине дуги, на которую он опирается:</p>"
        + line(r"\alpha=\frac{\beta}{2}")
        + line(
            r"\alpha=\frac{"
            + value(intercepted)
            + "}{2}"
            + DEG
            + "="
            + value(m.answer)
            + DEG
        )
    )


def _quad_ratio(m):
    b, c = m.given[1:3]
    unit = 360 / sum(m.given)
    return (
        _partition(m)
        + "<p>Угол A опирается на дугу BCD, состоящую из дуг BC и CD:</p>"
        + line(
            arc("BCD") + "=" + arc("BC") + "+" + arc("CD") + "=" + bracket(b + c) + "x"
        )
        + line(r"\angle A=\frac{1}{2}" + arc("BCD"))
        + line(
            r"\angle A=\frac{"
            + bracket(b + c)
            + r"\cdot "
            + bracket(unit)
            + "}{2}"
            + DEG
            + "="
            + value(m.answer)
            + DEG
        )
    )


def _four_arcs(m):
    c, d = m.given[2:]
    return (
        "<p>Вписанный угол B равен половине дуги ADC, на которую он опирается. Эта дуга состоит из AD и CD:</p>"
        + line(arc("ADC") + "=" + arc("AD") + "+" + arc("CD"))
        + line(
            arc("ADC")
            + "="
            + value(d)
            + DEG
            + "+"
            + value(c)
            + DEG
            + "="
            + value(c + d)
            + DEG
        )
        + line(r"\angle B=\frac{1}{2}" + arc("ADC"))
        + line(
            r"\angle B=\frac{"
            + value(c + d)
            + "}{2}"
            + DEG
            + "="
            + value(m.answer)
            + DEG
        )
    )


def _combined(m):
    a, b = m.given
    if m.mode == "cyclic_sum":
        body = (
            line(arc("AD") + r"=2\angle ABD=" + value(2 * a) + DEG)
            + line(arc("CD") + r"=2\angle CAD=" + value(2 * b) + DEG)
            + line(arc("ADC") + "=" + arc("AD") + "+" + arc("CD"))
            + line(r"\angle ABC=\frac{1}{2}" + arc("ADC") + r"=\angle ABD+\angle CAD")
            + line(
                r"\angle ABC="
                + value(a)
                + DEG
                + "+"
                + value(b)
                + DEG
                + "="
                + value(m.answer)
                + DEG
            )
        )
    else:
        body = (
            line(arc("ADC") + r"=2\angle ABC=" + value(2 * a) + DEG)
            + line(arc("AD") + r"=2\angle ABD=" + value(2 * b) + DEG)
            + line(arc("CD") + "=" + arc("ADC") + "-" + arc("AD"))
            + line(r"\angle CAD=\frac{1}{2}" + arc("CD") + r"=\angle ABC-\angle ABD")
            + line(
                r"\angle CAD="
                + value(a)
                + DEG
                + "-"
                + value(b)
                + DEG
                + "="
                + value(m.answer)
                + DEG
            )
        )
    return (
        "<p>Вписанный угол равен половине дуги, на которую он опирается. Выразим нужную дугу через дуги AD и CD:</p>"
        + body
    )


def _largest(m):
    a, b = m.given
    return (
        "<p>Сумма противоположных углов вписанного четырёхугольника равна 180°. Обозначим два известных угла через a и b:</p>"
        + line(
            "a+b=" + value(a) + DEG + "+" + value(b) + DEG + "=" + value(a + b) + DEG
        )
        + "<p>Эта сумма не равна 180°, поэтому данные углы расположены при соседних вершинах. Найдём углы, противоположные им:</p>"
        + line(
            r"\gamma=180^{\circ}-a=180^{\circ}-"
            + value(a)
            + DEG
            + "="
            + value(180 - a)
            + DEG
        )
        + line(
            r"\delta=180^{\circ}-b=180^{\circ}-"
            + value(b)
            + DEG
            + "="
            + value(180 - b)
            + DEG
        )
        + "<p>Больший из оставшихся углов лежит напротив меньшего из данных:</p>"
        + line(r"\alpha=\max\{\gamma,\delta\}=" + value(m.answer) + DEG)
    )


def render(m):
    if m.mode == "cyclic_opposite":
        return _opposite(m)
    methods = {
        "triangle_arc_ratio": _triangle_ratio,
        "cyclic_arc_ratio": _quad_ratio,
        "cyclic_four_arcs": _four_arcs,
        "cyclic_sum": _combined,
        "cyclic_difference": _combined,
        "cyclic_largest": _largest,
    }
    return solution_section("Решение", methods[m.mode](m))
