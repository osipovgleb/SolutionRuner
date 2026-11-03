"""The parent's direct and inverse diagonal products and both thirty-degree methods."""

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from .rectangle_proofs import value


def _thirty(m):
    h = m.given[0]
    first = (
        "<p>Площадь ромба равна произведению квадрата длины его стороны на синус его угла. С другой стороны, она равна произведению основания на высоту. Пусть сторона ромба равна a, а данная высота — h:</p>"
        + line(r"S=a^2\sin 30^{\circ}")
        + line("S=ah")
        + line(r"\sin 30^{\circ}=\frac{1}{2}")
        + "<p>Приравняем выражения площади. Длина стороны положительна, поэтому можно разделить равенство на a:</p>"
        + line(r"\frac{a^2}{2}=ah")
        + line(r"\frac{a}{2}=h")
        + line("a=2h")
        + line(r"a=2\cdot " + value(h) + "=" + value(m.a))
        + "<p>Подставим сторону и высоту в формулу площади:</p>"
        + line("S=" + value(m.a) + r"\cdot " + value(h) + "=" + value(m.area))
    )
    second = (
        "<p>Пусть острым углом ромба является угол A. Проведём высоту BH к стороне AD и рассмотрим прямоугольный треугольник ABH. Катет, лежащий против угла в 30°, равен половине гипотенузы:</p>"
        + line(r"\angle A=30^{\circ}")
        + line("BH=" + value(h))
        + line("AB=2BH")
        + line(r"AB=2\cdot " + value(h))
        + line("AB=" + value(m.a))
        + "<p>В ромбе все стороны равны. Используем найденную сторону и данную высоту:</p>"
        + line("AD=AB")
        + line(r"S_{ABCD}=AD\cdot BH")
        + line(r"S_{ABCD}=" + value(m.a) + r"\cdot " + value(h) + "=" + value(m.area))
    )
    return solution_section("Решение", first) + solution_section(
        "Альтернативное решение.", second
    )


def _diagonals(m):
    first, second = m.diagonals
    return (
        "<p>Площадь ромба равна половине произведения длин его диагоналей. Обозначим данные длины d₁ и d₂:</p>"
        + line("d_1=" + value(first) + r",\quad d_2=" + value(second))
        + line(r"S=\frac{d_1d_2}{2}")
        + "<p>Подставим обе длины, перемножим их и разделим произведение на два:</p>"
        + line(r"S=\frac{" + value(first) + r"\cdot " + value(second) + "}{2}")
        + line(r"S=\frac{" + value(first * second) + "}{2}")
        + line("S=" + value(m.area))
    )


def _other(m):
    area, known = m.given
    return (
        "<p>Площадь ромба равна половине произведения длин его диагоналей. Пусть a — длина искомой диагонали, d — длина известной:</p>"
        + line(r"S=\frac{ad}{2}")
        + line("S=" + value(area) + r",\quad d=" + value(known))
        + "<p>Подставим данные и решим уравнение относительно a:</p>"
        + line(value(known / 2) + "a=" + value(area))
        + line(r"a=\frac{" + value(area) + "}{" + value(known / 2) + "}")
        + line(r"a=\frac{2S}{d}")
        + line(
            r"a=\frac{2\cdot "
            + value(area)
            + "}{"
            + value(known)
            + "}="
            + value(m.answer)
        )
    )


def _factor(m):
    area, factor = m.given
    return (
        "<p>Площадь ромба равна половине произведения длин его диагоналей. Пусть меньшая диагональ равна a, тогда большая равна k·a, где k — данный множитель:</p>"
        + line("k=" + value(factor))
        + line(r"S=\frac{a\cdot ka}{2}")
        + line(r"S=\frac{k}{2}a^2")
        + "<p>Подставим площадь и множитель, затем выразим квадрат меньшей диагонали:</p>"
        + line(value(factor / 2) + "a^2=" + value(area))
        + line(r"a^2=\frac{2S}{k}")
        + line(r"a^2=\frac{2\cdot " + value(area) + "}{" + value(factor) + "}")
        + "<p>Длина диагонали положительна, поэтому выбираем положительный квадратный корень:</p>"
        + line(r"a=\sqrt{\frac{2\cdot " + value(area) + "}{" + value(factor) + "}}")
        + line("a=" + value(m.answer))
    )


def render(m):
    if m.mode == "thirty":
        return _thirty(m)
    return solution_section(
        "Решение",
        {"diagonals": _diagonals, "other": _other, "factor": _factor}[m.mode](m),
    )
