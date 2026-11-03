"""Preserve the linear angle and perimeter arguments of the reviewed parents."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from .rectangle_proofs import bracket, value


def _sum(m):
    kind = "острых" if m.first < 90 else "тупых"
    return (
        "<p>Сумма углов, прилежащих к одной стороне параллелограмма, равна 180°. Данная сумма отличается от 180°, поэтому речь идёт о противоположных равных углах. Обозначим каждый из них x, а один из оставшихся углов y:</p>"
        + line("2x=" + value(m.given[0]))
        + line(r"x=\frac{" + value(m.given[0]) + "}{2}")
        + line("x=" + value(m.first))
        + "<p>Найдена величина каждого из двух "
        + kind
        + " углов. Оставшиеся углы также равны; каждый дополняет найденный до 180°:</p>"
        + line(r"x+y=180^{\circ}")
        + line(r"y=180^{\circ}-x")
        + line(r"y=180^{\circ}-" + value(m.first) + "=" + value(m.answer))
    )


def _difference(m):
    difference = m.given[0]
    return (
        "<p>Противоположные углы параллелограмма равны, поэтому два различных угла прилежат к одной стороне и в сумме дают 180°. Обозначим больший угол D; другой меньше него на данную величину:</p>"
        + line(r"\angle A+\angle D=180^{\circ}")
        + line(r"\angle A=\angle D-" + value(difference))
        + line(r"\angle D+(\angle D-" + value(difference) + r")=180^{\circ}")
        + "<p>Раскроем скобки, перенесём разность в правую часть и разделим на два:</p>"
        + line(r"2\angle D=180^{\circ}+" + value(difference))
        + line(r"2\angle D=" + value(180 + difference))
        + line(r"\angle D=\frac{" + value(180 + difference) + "}{2}=" + value(m.answer))
    )


def _split(m):
    first, second = m.given
    bigger = "A" if m.first >= m.second else "B"
    return (
        "<p>Диагональ AC делит угол A на углы BAC и CAD. Поэтому сначала сложим данные углы:</p>"
        + line(r"\angle BAC=" + value(first) + r",\quad\angle CAD=" + value(second))
        + line(r"\angle A=\angle BAC+\angle CAD")
        + line(r"\angle A=" + value(first) + "+" + value(second) + "=" + value(m.first))
        + "<p>Сумма углов, прилежащих к одной стороне параллелограмма, равна 180°. Найдём соседний угол B:</p>"
        + line(r"\angle B=180^{\circ}-\angle A")
        + line(r"\angle B=180^{\circ}-" + value(m.first) + "=" + value(m.second))
        + "<p>Противоположные углы попарно равны. Сравнив два полученных значения, выбираем больший угол:</p>"
        + line(r"\max(\angle A,\angle B)=\angle " + bigger + "=" + value(m.answer))
    )


def _angle_ratio(m):
    small, large = sorted(m.given)
    factor = large / small
    return (
        "<p>Данные углы не равны, поэтому они соседние: противоположные углы параллелограмма равны. Сумма углов, прилежащих к одной стороне, равна 180°. Обозначим меньший угол A, больший B:</p>"
        + line(r"\angle B=" + value(factor) + r"\angle A")
        + line(r"\angle A+\angle B=180^{\circ}")
        + line(r"\angle B=" + value(factor) + r"(180^{\circ}-\angle B)")
        + "<p>Раскроем скобки и соберём слагаемые с углом B в левой части:</p>"
        + line(value(1 + factor) + r"\angle B=" + value(180 * factor))
        + line(
            r"\angle B=\frac{" + value(180 * factor) + "}{" + value(1 + factor) + "}"
        )
        + line(r"\angle B=" + value(m.answer))
    )


def _side_difference(m):
    perimeter, difference = m.given
    return (
        "<p>Противоположные стороны параллелограмма попарно равны. Пусть AB — меньшая сторона, AD — большая. Выразим большую сторону через меньшую и запишем периметр:</p>"
        + line("AD=AB+" + value(difference))
        + line("P=2(AB+AD)")
        + line("P=2(AB+AB+" + value(difference) + ")")
        + line("P=4AB+" + value(2 * difference))
        + "<p>Подставим данный периметр и решим линейное уравнение:</p>"
        + line("4AB+" + value(2 * difference) + "=" + value(perimeter))
        + line("4AB=" + value(perimeter - 2 * difference))
        + line(
            r"AB=\frac{" + value(perimeter - 2 * difference) + "}{4}=" + value(m.answer)
        )
    )


def _side_known(m):
    perimeter, known = m.given
    return (
        "<p>Противоположные стороны параллелограмма попарно равны. Обозначим меньшую сторону AB, искомую большую AD. Применим ту же формулу периметра:</p>"
        + line("AB=" + value(known))
        + line("P=2(AB+AD)")
        + line(value(perimeter) + "=2(" + value(known) + "+AD)")
        + "<p>Разделим равенство на два и вычтем известную сторону:</p>"
        + line(value(perimeter / 2) + "=" + value(known) + "+AD")
        + line(r"AD=\frac{P}{2}-AB")
        + line(
            "AD=" + value(perimeter / 2) + "-" + value(known) + "=" + value(m.answer)
        )
    )


def _side_ratio(m):
    small, large = sorted(m.given[:2])
    perimeter = m.given[2]
    ratio, coefficient = small / large, 2 * (1 + small / large)
    x = perimeter / (2 * (small + large))
    first = (
        "<p>Противоположные стороны параллелограмма попарно равны. Обозначим меньшую сторону AB, большую AD. Выразим AB через AD по данному отношению:</p>"
        + line("AB=" + value(ratio) + "AD")
        + line("P=2(AB+AD)")
        + line("P=2(" + value(ratio) + "AD+AD)")
        + line("P=" + value(coefficient) + "AD")
        + "<p>Подставим периметр и разделим на коэффициент при AD:</p>"
        + line("P=" + value(perimeter))
        + line(r"AD=\frac{P}{" + value(coefficient) + "}")
        + line(
            r"AD=\frac{"
            + value(perimeter)
            + "}{"
            + value(coefficient)
            + "}="
            + value(m.answer)
        )
    )
    second = (
        "<p>Пусть меньшая сторона параллелограмма равна r·x, большая s·x, где r и s — соответственно меньший и больший члены данного отношения. Запишем уравнение периметра:</p>"
        + line("AB=" + value(small) + r"x,\quad AD=" + value(large) + "x")
        + line("2(" + value(small) + "x+" + value(large) + "x)=" + value(perimeter))
        + line(value(small + large) + "x=" + value(perimeter / 2))
        + line(r"x=\frac{" + value(perimeter / 2) + "}{" + value(small + large) + "}")
        + line("x=" + value(x))
        + "<p>Умножим найденный общий множитель на больший член отношения, чтобы получить искомую сторону:</p>"
        + line("AD=" + value(large) + r"\cdot " + bracket(x) + "=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Альтернативное решение.", second
    )


def render(m):
    if m.mode == "side_ratio":
        return _side_ratio(m)
    method = {
        "angle_sum": _sum,
        "angle_difference": _difference,
        "angle_split": _split,
        "angle_ratio": _angle_ratio,
        "side_difference": _side_difference,
        "side_known": _side_known,
    }[m.mode]
    return solution_section("Решение", method(m))
