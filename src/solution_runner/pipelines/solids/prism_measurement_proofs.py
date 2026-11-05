"""Explain prism base geometry and the parent's requested volume, surface or height."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from .prism_model import MEASUREMENTS


def _triangle(m, perimeter):
    a, b = m.given[:2]
    rows = "<p>Основание — прямоугольный треугольник. Найдём необходимые площадь и периметр:</p>"
    if perimeter:
        rows += line("c^2=a^2+b^2") + line(
            r"c=\sqrt{" + bracket(a) + "^2+" + bracket(b) + "^2}=" + value(m.side)
        )
    rows += line(r"B=\frac{ab}{2}") + line(
        r"B=\frac{" + value(a) + r"\cdot" + value(b) + "}{2}=" + value(m.area)
    )
    return rows + (line("P=a+b+c=" + value(m.perimeter)) if perimeter else "")


def _rhombus(m):
    d1, d2 = m.given[:2]
    return (
        "<p>Найдём сторону ромба по его диагоналям, затем площадь и периметр основания:</p>"
        + line(r"a=\frac{1}{2}\sqrt{d_1^2+d_2^2}")
        + line(
            r"a=\frac{1}{2}\sqrt{"
            + bracket(d1)
            + "^2+"
            + bracket(d2)
            + "^2}="
            + value(m.side)
        )
        + line(
            r"B=\frac{d_1d_2}{2}=\frac{"
            + value(d1)
            + r"\cdot"
            + value(d2)
            + "}{2}="
            + value(m.area)
        )
        + line("P=4a=" + value(m.perimeter))
    )


def _square(m):
    a = m.given[0]
    return (
        "<p>Основание правильной четырёхугольной призмы — квадрат. Найдём его площадь и периметр:</p>"
        + line("B=a^2")
        + line("B=" + bracket(a) + "^2=" + value(m.area))
        + line("P=4a")
        + line(r"P=4\cdot" + bracket(a) + "=" + value(m.perimeter))
    )


def _hex_volume(m):
    a = m.given[0]
    return (
        "<p>Правильный шестиугольник состоит из шести равносторонних треугольников. Найдём площадь основания:</p>"
        + line(r"B=6\cdot\frac{\sqrt{3}}{4}a^2")
        + line(r"B=\frac{3\sqrt{3}}{2}a^2")
        + line(r"B=\frac{3\sqrt{3}}{2}\cdot" + bracket(a) + "^2=" + value(m.area))
        + "<p>Объём прямой призмы равен произведению площади основания на высоту:</p>"
        + line(("H=a=" if m.kind == "hex_equal_volume" else "H=") + value(m.height))
        + line("V=BH")
        + line("V=" + bracket(m.area) + r"\cdot" + bracket(m.height))
        + line("V=" + value(m.answer))
    )


def _hex_lateral(m):
    a, h = m.given
    face = a * h
    return (
        "<p>Все шесть боковых граней правильной шестиугольной призмы — равные прямоугольники:</p>"
        + line("S_f=aH")
        + line("S=6S_f")
        + "<p>Найдём площадь одной грани и сложим площади шести граней:</p>"
        + line("S_f=" + bracket(a) + r"\cdot" + bracket(h) + "=" + value(face))
        + line(r"S=6\cdot" + bracket(face))
        + line("S=" + value(m.answer))
    )


def _normal(m):
    a, b, edge = m.given
    return (
        "<p>Перпендикулярное боковым рёбрам сечение — прямоугольный треугольник: его катеты равны данным расстояниям, поскольку две боковые грани перпендикулярны. Найдём периметр сечения:</p>"
        + line("c^2=a^2+b^2")
        + line(r"c=\sqrt{" + bracket(a) + "^2+" + bracket(b) + "^2}=" + value(m.side))
        + line("P=a+b+c=" + value(m.perimeter))
        + "<p>Площадь боковой поверхности равна произведению периметра перпендикулярного сечения на боковое ребро L; призма может быть наклонной:</p>"
        + line("S=PL")
        + line(
            "S="
            + bracket(m.perimeter)
            + r"\cdot"
            + bracket(edge)
            + "="
            + value(m.answer)
        )
    )


def _result(m, target):
    last = m.given[-1]
    if target == "height_volume":
        return (
            "<p>Выразим боковое ребро из формулы объёма прямой призмы:</p>"
            + line("V=BH")
            + line(r"H=\frac{V}{B}")
            + line(
                r"H=\frac{"
                + value(last)
                + "}{"
                + value(m.area)
                + "}="
                + value(m.answer)
            )
        )
    if target == "height_total":
        return (
            "<p>Выразим высоту из суммы площадей двух оснований и боковой поверхности:</p>"
            + line("S=2B+PH")
            + line(r"H=\frac{S-2B}{P}")
            + line(
                r"H=\frac{"
                + value(last)
                + r"-2\cdot"
                + bracket(m.area)
                + "}{"
                + value(m.perimeter)
                + "}="
                + value(m.answer)
            )
        )
    symbol = "V" if target == "volume" else "S"
    formula = "V=BH" if target == "volume" else "S=2B+PH"
    substitution = (
        bracket(m.area) + r"\cdot" + bracket(m.height)
        if target == "volume"
        else r"2\cdot"
        + bracket(m.area)
        + "+"
        + bracket(m.perimeter)
        + r"\cdot"
        + bracket(m.height)
    )
    return (
        "<p>Подставим найденные величины в формулу призмы:</p>"
        + line(formula)
        + line(symbol + "=" + substitution)
        + line(symbol + "=" + value(m.answer))
    )


def render(m):
    if m.kind == "normal_lateral":
        return _normal(m)
    if m.kind == "hex_lateral":
        return _hex_lateral(m)
    if m.base == "hexagon":
        return _hex_volume(m)
    target = MEASUREMENTS[m.kind][1]
    rows = (
        _triangle(m, target in {"total", "height_total"})
        if m.base == "triangle"
        else _rhombus(m)
        if m.base == "rhombus"
        else _square(m)
    )
    rows += _result(m, target)
    if m.kind == "rhombus_total":
        rows += (
            "<p><b>Примечание.</b> Диагонали ромба перпендикулярны и точкой пересечения делятся пополам. Поэтому используемая формула стороны следует из теоремы Пифагора:</p>"
            + line(
                r"a^2=\left(\frac{d_1}{2}\right)^2+\left(\frac{d_2}{2}\right)^2=\frac{d_1^2+d_2^2}{4}"
            )
            + line(r"a=\frac{1}{2}\sqrt{d_1^2+d_2^2}")
        )
    return rows
