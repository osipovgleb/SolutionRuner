"""Keep the parents' edge, space-diagonal, sphere-fraction and cutout methods."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value


def cube_around(m):
    r, a = m.q["r"], m.q["a"]
    rows = (
        "<p>Прямоугольный параллелепипед, описанный около сферы, является кубом. Его ребро равно диаметру сферы:</p>"
        + line("r=" + value(r))
        + line("a=2r")
        + line(r"a=2\cdot" + bracket(r) + "=" + value(a))
    )
    if m.kind == "cube_around_sphere_surface":
        return (
            rows
            + "<p>Поверхность куба состоит из шести равных квадратов:</p>"
            + line("S=6a^2")
            + line(r"S=6\cdot" + bracket(a) + "^2=" + value(m.answer))
        )
    return (
        rows
        + "<p>Объём куба равен кубу длины его ребра:</p>"
        + line("V=a^3")
        + line("V=" + bracket(a) + "^3=" + value(m.answer))
    )


def insphere_radius(m):
    a = m.q["a"]
    return (
        "<p>Найдём ребро куба по его объёму:</p>"
        + line("V=a^3")
        + line("V=" + value(m.given[0]))
        + line(r"a=\sqrt[3]{" + value(m.given[0]) + "}=" + value(a))
        + "<p>Радиус вписанной сферы равен половине ребра куба:</p>"
        + line(r"r=\frac{a}{2}")
        + line(r"r=\frac{" + value(a) + "}{2}=" + value(m.answer))
    )


def cube_in_sphere(m):
    r, a = m.given[0], m.q["a"]
    return (
        "<p>Диаметр описанного шара совпадает с пространственной диагональю куба:</p>"
        + line("d=2R")
        + line(r"d=2\cdot" + bracket(r) + "=" + value(2 * r))
        + line(r"d=a\sqrt{3}")
        + "<p>Найдём ребро куба, затем его объём:</p>"
        + line(r"a=\frac{d}{\sqrt{3}}")
        + line(r"a=\frac{" + value(2 * r) + r"}{\sqrt{3}}=" + value(a))
        + line("V=a^3")
        + line("V=" + bracket(a) + "^3=" + value(m.answer))
    )


def sphere_volume(m):
    a, r = m.q["a"], m.q["r"]
    if m.kind == "cube_circumsphere_volume":
        rows = (
            "<p>Пусть a — ребро куба, d — его диагональ. Радиус описанного шара равен половине диагонали:</p>"
            + line(r"d=a\sqrt{3}")
            + line(r"r=\frac{d}{2}=\frac{a\sqrt{3}}{2}")
            + line(r"r=\frac{" + bracket(a) + r"\cdot\sqrt{3}}{2}=" + value(r))
        )
    else:
        rows = (
            "<p>Радиус вписанного в куб шара равен половине длины ребра куба:</p>"
            + line("a=" + value(a))
            + line(r"r=\frac{a}{2}")
            + line(r"r=\frac{" + value(a) + "}{2}=" + value(r))
        )
    return (
        rows
        + "<p>Подставим радиус в формулу объёма шара и разделим результат на π:</p>"
        + line(r"V=\frac{4}{3}\pi r^3")
        + line(
            r"V=\frac{4}{3}\pi\cdot" + bracket(r) + "^3=" + bracket(m.answer) + r"\pi"
        )
        + line(r"\frac{V}{\pi}=" + value(m.answer))
    )


def cube_from_ball_volume(m):
    return (
        "<p>Ребро куба равно диаметру вписанного шара. Выразим объём куба через радиус шара:</p>"
        + line("a=2R")
        + line(r"V_{\mathrm{к}}=a^3=8R^3")
        + "<p>Из известного объёма шара найдём куб радиуса и подставим его в формулу объёма куба:</p>"
        + line(r"V_{\mathrm{ш}}=\frac{4}{3}\pi R^3=" + value(m.given[0]))
        + line(
            r"R^3=\frac{3\cdot" + bracket(m.given[0]) + r"}{4\pi}=" + value(m.q["r3"])
        )
        + line(r"V_{\mathrm{к}}=8\cdot" + bracket(m.q["r3"]) + "=" + value(m.answer))
    )


def sphere_part(m):
    vertex = m.kind == "sphere_vertex_part"
    why = (
        "Радиус сферы равен ребру куба. Три грани при вершине A делят сферу на восемь равных частей, одна из которых лежит внутри куба."
        if vertex
        else "Центр шара — середина ребра куба. Радиус не больше половины этого ребра, поэтому шар не выходит за торцевые грани. Две грани, содержащие ребро, выделяют четверть поверхности шара."
    )
    return (
        "<p>"
        + why
        + "</p>"
        + line("a=" + value(m.q["a"]))
        + line("r=" + value(m.q["r"]))
        + line(r"S_0=4\pi r^2")
        + "<p>Умножим полную площадь сферы на долю, содержащуюся внутри куба, и разделим результат на π:</p>"
        + line("S=" + value(m.q["fraction"]) + "S_0")
        + line(r"\frac{S}{\pi}=4\cdot" + bracket(m.q["fraction"]) + "r^2")
        + line(
            r"\frac{S}{\pi}=4\cdot"
            + bracket(m.q["fraction"])
            + r"\cdot"
            + bracket(m.q["r"])
            + "^2="
            + value(m.answer)
        )
    )


def cube_hole(m):
    b = m.q["b"]
    return (
        "<p>На рисунке показано внутреннее сквозное отверстие. К поверхности единичного куба добавляются четыре боковые грани вырезанной призмы:</p>"
        + line("S_0=6")
        + line(r"L=4bh=4\cdot" + bracket(b) + r"\cdot1=" + value(4 * b))
        + "<p>Из двух граней куба удалены основания призмы. Найдём площадь одного основания и вычтем две такие площади:</p>"
        + line("B=b^2=" + bracket(b) + "^2=" + value(b**2))
        + line("S=S_0+L-2B")
        + line(
            "S=6+" + value(4 * b) + r"-2\cdot" + bracket(b**2) + "=" + value(m.answer)
        )
    )
