"""Use base diagonals, incircle radii, lateral areas and shared heights."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def box(m):
    q = m.q
    rows = (
        "<p>Высота параллелепипеда равна высоте цилиндра. Основание параллелепипеда — квадрат со стороной, равной диаметру основания цилиндра:</p>"
        + line("a=2r")
        + line(r"a=2\cdot" + bracket(q["r"]) + "=" + value(q["a"]))
        + line("B=a^2=" + bracket(q["a"]) + "^2=" + value(q["B"]))
    )
    if m.kind == "box_cylinder_height":
        return (
            rows
            + "<p>Выразим общую высоту из формулы объёма параллелепипеда:</p>"
            + line("V=BH")
            + line(r"H=\frac{V}{B}")
            + line(
                r"H=\frac{"
                + value(m.given[1])
                + "}{"
                + value(q["B"])
                + "}="
                + value(m.answer)
            )
        )
    return (
        rows
        + "<p>Объём параллелепипеда равен произведению площади основания на высоту:</p>"
        + line("H=" + value(q["H"]))
        + line("V=BH")
        + line(
            "V=" + bracket(q["B"]) + r"\cdot" + bracket(q["H"]) + "=" + value(m.answer)
        )
    )


def cylinder_around(m):
    q = m.q
    if m.kind == "cylinder_around_triangle":
        a, b, coefficient = m.given
        rows = (
            "<p>По теореме Пифагора найдём гипотенузу треугольника в основании призмы. Она является диаметром основания описанного цилиндра:</p>"
            + line("d^2=a^2+b^2")
            + line("d^2=" + bracket(a) + "^2+" + bracket(b) + "^2=" + value(q["d2"]))
            + line(r"d=\sqrt{" + value(q["d2"]) + "}")
        )
    else:
        a, coefficient = m.given
        rows = (
            "<p>Диагональ квадрата в основании призмы является диаметром основания описанного цилиндра:</p>"
            + line(r"d=a\sqrt{2}")
            + line("d^2=2a^2")
            + line(r"d^2=2\cdot" + bracket(a) + "^2=" + value(q["d2"]))
        )
    return (
        rows
        + "<p>Высота цилиндра равна боковому ребру прямой призмы. Подставим диаметр и высоту в формулу объёма:</p>"
        + line(r"H=\frac{" + value(coefficient) + r"}{\pi}")
        + line(r"V=\frac{\pi d^2}{4}H")
        + line(
            r"V=\frac{\pi\cdot"
            + bracket(q["d2"])
            + r"}{4}\cdot\frac{"
            + value(coefficient)
            + r"}{\pi}="
            + value(m.answer)
        )
    )


def regular_prism(m):
    q = m.q
    n, relation, explanation = {
        "square_cylinder_lateral": (
            4,
            "2r",
            "Сторона квадрата в основании призмы равна диаметру цилиндра.",
        ),
        "square_cylinder_height": (
            4,
            "2r",
            "Сторона квадрата в основании призмы равна диаметру цилиндра.",
        ),
        "triangle_around_cylinder_lateral": (
            3,
            r"2\sqrt{3}r",
            "Сторона правильного треугольника выражается через радиус вписанной окружности.",
        ),
        "triangle_in_cylinder_lateral": (
            3,
            r"\sqrt{3}r",
            "Сторона правильного треугольника выражается через радиус описанной окружности.",
        ),
        "hexagon_cylinder_lateral": (
            6,
            r"\frac{2}{\sqrt{3}}r",
            "Сторона правильного шестиугольника выражается через радиус вписанной окружности.",
        ),
    }[m.kind]
    rows = (
        "<p>"
        + explanation
        + " Высота призмы равна высоте цилиндра.</p>"
        + line("r=" + value(q["r"]))
        + line("a=" + relation)
        + line(
            "a=" + relation.removesuffix("r") + bracket(q["r"]) + "=" + value(q["a"])
        )
        + line("P=" + str(n) + "a=" + value(q["P"]))
        + "<p>Площадь боковой поверхности прямой призмы равна произведению периметра основания на высоту:</p>"
        + line("L=PH")
    )
    if m.kind == "square_cylinder_height":
        return (
            rows
            + line(r"H=\frac{L}{P}")
            + line(
                r"H=\frac{"
                + value(m.given[1])
                + "}{"
                + value(q["P"])
                + "}="
                + value(m.answer)
            )
        )
    return (
        rows
        + line("H=" + value(q["H"]))
        + line(
            "L=" + bracket(q["P"]) + r"\cdot" + bracket(q["H"]) + "=" + value(m.answer)
        )
    )


def pyramid_cone(m):
    q = m.q
    return (
        "<p>Квадрат в основании пирамиды вписан в окружность основания конуса. Радиус конуса равен половине диагонали квадрата:</p>"
        + line(r"d=a\sqrt{2}")
        + line(r"r=\frac{d}{2}=\frac{a\sqrt{2}}{2}")
        + line(r"r=\frac{" + bracket(q["a"]) + r"\cdot\sqrt{2}}{2}=" + value(q["r"]))
        + "<p>Высота конуса равна высоте пирамиды. Подставим радиус и высоту в формулу объёма и разделим на π:</p>"
        + line("H=" + value(q["H"]))
        + line(r"V=\frac{1}{3}\pi r^2H")
        + line(
            r"\frac{V}{\pi}=\frac{1}{3}\cdot"
            + bracket(q["r"])
            + r"^2\cdot"
            + bracket(q["H"])
            + "="
            + value(m.answer)
        )
    )


def cone_sphere(m):
    q = m.q
    rows = (
        "<p>Центр сферы совпадает с центром основания конуса. Поэтому радиус основания и высота конуса равны радиусу сферы:</p>"
        + line("h=r")
        + "<p>Образующая, высота и радиус основания конуса связаны теоремой Пифагора:</p>"
        + line("l^2=h^2+r^2")
        + line("l^2=2r^2")
        + line(r"l=r\sqrt{2}")
    )
    if m.kind == "cone_sphere_radius":
        return rows + line(
            r"r=\frac{l}{\sqrt{2}}=\frac{"
            + bracket(m.given[0])
            + r"}{\sqrt{2}}="
            + value(m.answer)
        )
    return rows + line("l=" + bracket(q["r"]) + r"\cdot\sqrt{2}=" + value(m.answer))
