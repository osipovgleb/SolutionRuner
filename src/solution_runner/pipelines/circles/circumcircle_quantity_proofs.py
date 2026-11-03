"""Preserve diameter, Pythagoras, sine and equilateral-hexagon parent methods."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section

MODES = {
    "right_radius",
    "right_hypotenuse",
    "right_legs",
    "isosceles_diameter",
    "sine_radius",
    "sine_side",
    "hexagon_side",
    "hexagon_diameter",
}


def _right(m):
    if m.mode == "right_legs":
        a, b = m.given[:2]
        hyp = sp.sqrt(a * a + b * b)
        return (
            "<p>Радиус окружности, описанной вокруг прямоугольного треугольника, равен половине гипотенузы. Найдём гипотенузу по теореме Пифагора:</p>"
            + line("AB^2=AC^2+BC^2")
            + line(r"AB=\sqrt{AC^2+BC^2}")
            + line(r"AB=\sqrt{" + bracket(a) + "^2+" + bracket(b) + "^2}=" + value(hyp))
            + "<p>Гипотенуза AB является диаметром описанной окружности:</p>"
            + line(r"R=\frac{AB}{2}")
            + line(r"R=\frac{" + value(hyp) + "}{2}=" + value(m.answer))
        )
    intro = "<p>Прямой вписанный угол C опирается на диаметр окружности, поэтому гипотенуза AB является диаметром D:</p>"
    if m.mode == "right_radius":
        hyp = m.given[0]
        return (
            intro
            + line("AB=" + value(hyp))
            + line("D=AB")
            + line(r"R=\frac{D}{2}")
            + line(r"R=\frac{" + value(hyp) + "}{2}=" + value(m.answer))
        )
    return (
        intro
        + line("D=2R")
        + line(r"D=2\cdot " + bracket(m.given[0]) + "=" + value(m.answer))
        + line("AB=D")
        + line("AB=" + value(m.answer))
    )


def _isosceles(m):
    side = m.given[0]
    return (
        "<p>Сумма двух равных углов при основании треугольника равна 60°, поэтому каждый из них равен 30°:</p>"
        + line(r"\angle A+\angle B=180^{\circ}-120^{\circ}=60^{\circ}")
        + line(r"\angle A=\angle B=\frac{60^{\circ}}{2}=30^{\circ}")
        + "<p>По теореме синусов диаметр описанной окружности равен отношению стороны к синусу противолежащего угла:</p>"
        + line(r"d=\frac{BC}{\sin A}")
        + line(r"d=\frac{" + value(side) + r"}{\sin30^{\circ}}")
        + line(r"d=\frac{" + value(side) + r"}{\frac{1}{2}}=" + value(m.answer))
    )


def _sine(m):
    amount, angle = m.given
    sine = sp.simplify(sp.sin(sp.pi * angle / 180))
    intro = "<p>По теореме синусов отношение стороны к синусу противолежащего угла равно диаметру описанной окружности:</p>"
    known = line(r"\sin C=\sin" + value(angle) + r"^{\circ}=" + value(sine))
    if m.mode == "sine_radius":
        return (
            intro
            + line(r"R=\frac{AB}{2\sin C}")
            + known
            + line(r"R=\frac{" + value(amount) + r"}{2\cdot " + bracket(sine) + "}")
            + line("R=" + value(m.answer))
        )
    return (
        intro
        + line(r"AB=2R\sin C")
        + known
        + line(r"AB=2\cdot " + bracket(amount) + r"\cdot " + bracket(sine))
        + line("AB=" + value(m.answer))
    )


def _hexagon(m, pictures):
    if m.mode == "hexagon_side":
        return (
            pictures["equilateral"]
            + "<p>Соединим центр окружности O с соседними вершинами A и B правильного шестиугольника. Центральный угол равен:</p>"
            + line(r"\angle AOB=\frac{360^{\circ}}{6}=60^{\circ}")
            + line("AO=OB=R")
            + "<p>Треугольник AOB равнобедренный с углом при вершине 60°, значит, он равносторонний. Поэтому сторона шестиугольника равна радиусу:</p>"
            + line("AB=AO")
            + line("AB=R=" + value(m.answer))
        )
    perimeter = m.given[0]
    side = perimeter / 6
    return (
        "<p>Периметр — это сумма длин сторон, а стороны правильного шестиугольника равны между собой. Поэтому каждая из сторон равна:</p>"
        + line(r"a=\frac{P}{6}")
        + line(r"a=\frac{" + value(perimeter) + "}{6}=" + value(side))
        + "<p>Радиус описанной окружности равен стороне правильного шестиугольника, а диаметр вдвое больше:</p>"
        + line("D=2R=2a")
        + line(r"D=2\cdot " + bracket(side) + "=" + value(m.answer))
        + "<p><b>Примечание.</b></p><p>Докажем, что радиус равен стороне. Треугольник AOB равносторонний, поскольку его боковые стороны — радиусы и угол при вершине равен 60°:</p>"
        + line("AO=OB=R")
        + line(r"\angle AOB=\frac{360^{\circ}}{6}=60^{\circ}")
        + line("OA=AB=R")
    )


def render(m, pictures):
    if m.mode.startswith("right_"):
        body = _right(m)
    elif m.mode == "isosceles_diameter":
        body = _isosceles(m)
    elif m.mode.startswith("sine_"):
        body = _sine(m)
    else:
        body = _hexagon(m, pictures)
    return solution_section("Решение", body)
