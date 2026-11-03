"""Keep the equilateral-triangle parent methods and their alternative placements."""

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section

MODES = {
    "equilateral_radius_height",
    "equilateral_height_radius",
    "equilateral_radius_side",
    "equilateral_side_radius",
}


def _radius_height(m):
    return (
        "<p>Радиус окружности, вписанной в равносторонний треугольник, равен одной трети его высоты. Обозначим высоту через h и подставим данное значение:</p>"
        + line("h=" + value(m.given[0]))
        + line(r"r=\frac{h}{3}")
        + line(r"r=\frac{" + value(m.given[0]) + "}{3}")
        + line("r=" + value(m.answer))
    )


def _height_radius(m):
    radius, height = m.given[0], m.answer
    first = (
        "<p>Радиус вписанной окружности равен отношению удвоенной площади к периметру. В правильном треугольнике все стороны равны. Обозначим сторону AB через a:</p>"
        + line(r"r=\frac{2S_{ABC}}{P_{ABC}}")
        + line(r"S_{ABC}=\frac{1}{2}a^2\sin60^{\circ}")
        + line(r"P_{ABC}=3a")
        + line(r"r=\frac{a\sin60^{\circ}}{3}")
        + "<p>Высота равна a·sin 60°. Выразим сторону через высоту и сократим синус:</p>"
        + line(r"a=\frac{h}{\sin60^{\circ}}")
        + line(r"r=\frac{h}{\sin60^{\circ}}\cdot\frac{\sin60^{\circ}}{3}=\frac{h}{3}")
        + line("h=3r=3\\cdot " + bracket(radius) + "=" + value(height))
    )
    second = (
        "<p>Высота правильного треугольника равна трём радиусам вписанной окружности. Поэтому:</p>"
        + line("h=3r")
        + line("h=3\\cdot " + bracket(radius))
        + line("h=" + value(height))
    )
    return first, second


def _radius_side(m):
    side = m.given[0]
    return (
        "<p>Радиус вписанной в треугольник окружности равен отношению площади к полупериметру. В равностороннем треугольнике угол BAC равен 60°:</p>"
        + line(r"r=\frac{S_{ABC}}{p_{ABC}}")
        + line(r"S_{ABC}=\frac{1}{2}a^2\sin60^{\circ}")
        + line(r"p_{ABC}=\frac{3a}{2}")
        + line(r"r=\frac{a\sin60^{\circ}}{3}")
        + line(
            r"r=\frac{"
            + value(side)
            + r"}{3}\cdot\frac{\sqrt{3}}{2}="
            + value(m.answer)
        )
        + "<p><b>Примечание.</b></p><p>Другой способ состоит в использовании формулы радиуса вписанной окружности через сторону правильного треугольника:</p>"
        + line(
            r"r=\frac{a\sqrt{3}}{6}=\frac{"
            + bracket(side)
            + r"\cdot\sqrt{3}}{6}="
            + value(m.answer)
        )
    )


def _side_radius(m):
    radius = m.given[0]
    return (
        "<p>Известно соотношение между радиусом вписанной окружности и стороной правильного треугольника. Подставим данный радиус и выразим сторону:</p>"
        + line(r"r=\frac{\sqrt{3}}{6}a")
        + line(r"\frac{\sqrt{3}}{6}a=" + value(radius))
        + line(r"a=\frac{6r}{\sqrt{3}}")
        + line(r"a=\frac{6\cdot " + bracket(radius) + r"}{\sqrt{3}}=" + value(m.answer))
    )


def render(m, pictures):
    if m.mode == "equilateral_height_radius":
        first, second = _height_radius(m)
        return solution_section("Решение", first) + solution_section(
            "Приведем другое решение", second
        )
    method = {
        "equilateral_radius_height": _radius_height,
        "equilateral_radius_side": _radius_side,
        "equilateral_side_radius": _side_radius,
    }[m.mode]
    return solution_section("Решение", method(m))
