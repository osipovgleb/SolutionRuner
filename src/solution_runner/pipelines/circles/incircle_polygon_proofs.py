"""Preserve the rhombus height methods and all three hexagon constructions."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section

MODES = {"rhombus_radius", "rhombus_side", "hexagon_side", "hexagon_radius"}


def _rhombus(m, pictures):
    side = m.given[0] if m.mode == "rhombus_radius" else m.answer
    radius = side / 4
    height = side / 2
    first = (
        pictures["height"]
        + "<p>Радиус r вписанной в ромб окружности вдвое меньше его высоты d. Высота BH образует со стороной AB прямоугольный треугольник ABH:</p>"
        + line(r"d=BH=AB\sin\angle DAB")
        + line(r"\sin\angle DAB=\sin30^{\circ}=\frac{1}{2}")
    )
    if m.mode == "rhombus_radius":
        first += (
            line(r"r=\frac{d}{2}=\frac{AB\sin\angle DAB}{2}")
            + line(r"r=\frac{" + bracket(side) + r"\cdot\frac{1}{2}}{2}")
            + line("r=" + value(radius))
        )
        second = (
            "<p>Проведём высоту ромба. В прямоугольном треугольнике катет, лежащий против угла в 30°, равен половине гипотенузы. Поэтому высота ромба равна:</p>"
            + line(r"BH=\frac{AB}{2}")
            + line(r"BH=\frac{" + value(side) + "}{2}=" + value(height))
            + "<p>Радиус вписанной окружности равен половине высоты:</p>"
            + line(r"r=\frac{BH}{2}")
            + line(r"r=\frac{" + value(height) + "}{2}=" + value(radius))
        )
    else:
        first += (
            line(r"BH=d=2r=2\cdot " + bracket(radius) + "=" + value(height))
            + line(r"AB=\frac{BH}{\sin\angle DAB}=\frac{2r}{\sin30^{\circ}}")
            + line(r"AB=\frac{" + value(height) + r"}{\frac{1}{2}}=" + value(side))
        )
        second = (
            "<p>Треугольник ABH — прямоугольный. Высота ромба равна диаметру вписанной окружности:</p>"
            + line(r"BH=2r")
            + line(r"BH=2\cdot " + bracket(radius) + "=" + value(height))
            + "<p>Катет, лежащий против угла в 30°, равен половине гипотенузы. Найдём сторону ромба:</p>"
            + line("AB=2BH")
            + line(r"AB=2\cdot " + bracket(height) + "=" + value(side))
        )
    return solution_section("Решение", first) + solution_section(
        "Альтернативное решение.", second
    )


def _hexagon_side(m, pictures):
    radius = m.given[0]
    first = (
        pictures["tangent"]
        + "<p>Пусть точка O — центр окружности. Треугольник AOF равнобедренный с углом при вершине 60°, поэтому он равносторонний. Радиус OH является его высотой, биссектрисой и медианой:</p>"
        + line(r"\angle HOF=\frac{60^{\circ}}{2}=30^{\circ}")
        + line(r"HF=OH\tg\angle HOF")
        + line(r"AF=2HF=2OH\tg30^{\circ}")
        + line(r"AF=2\cdot " + bracket(radius) + r"\cdot\frac{1}{\sqrt{3}}")
        + line("AF=" + value(m.answer))
    )
    second = (
        "<p>Воспользуемся соотношением между стороной a правильного шестиугольника и радиусом r вписанной в него окружности:</p>"
        + line(r"a=\frac{2r}{\sqrt{3}}")
        + line(r"a=\frac{2\cdot " + bracket(radius) + r"}{\sqrt{3}}")
        + line("a=" + value(m.answer))
    )
    return solution_section("Решение", first) + solution_section(
        "Альтернативное решение.", second
    )


def _hexagon_cosine(m, pictures):
    side = m.given[0]
    diagonal = 2 * m.answer
    return (
        pictures["cosine"]
        + "<p>Угол между сторонами правильного шестиугольника равен 120°. Обозначим его сторону через a. Применим в треугольнике ABC теорему косинусов:</p>"
        + line(r"AC=\sqrt{AB^2+BC^2-2AB\cdot BC\cos120^{\circ}}")
        + line(r"AC=\sqrt{a^2+a^2-2a^2\cdot(-\frac{1}{2})}")
        + line(r"AC=a\sqrt{3}=" + bracket(side) + r"\cdot\sqrt{3}=" + value(diagonal))
        + "<p>Длина AC равна диаметру вписанной окружности. Поэтому:</p>"
        + line(r"r=\frac{AC}{2}")
        + line(r"r=\frac{" + value(diagonal) + "}{2}=" + value(m.answer))
    )


def _hexagon_pythagoras(m, pictures):
    side = m.given[0]
    return (
        pictures["pythagoras"]
        + "<p>Соединим центр O вписанной окружности с вершинами шестиугольника. Получим шесть равных равнобедренных треугольников. Угол при вершине O равен:</p>"
        + line(r"\angle AOB=\frac{360^{\circ}}{6}=60^{\circ}")
        + "<p>Следовательно, треугольник AOB равносторонний со стороной a. Радиус вписанной окружности является его биссектрисой, медианой и высотой. По теореме Пифагора:</p>"
        + line(r"r=\sqrt{AO^2-\left(\frac{AB}{2}\right)^2}")
        + line(r"r=\sqrt{" + bracket(side) + "^2-" + bracket(side / 2) + "^2}")
        + line(r"r=\sqrt{" + value(sp.simplify(3 * side**2 / 4)) + "}")
        + line("r=" + value(m.answer))
    )


def _hexagon_sine(m, pictures):
    side = m.given[0]
    return (
        "<p><b>Приведем еще одно решение</b>.</p>"
        + pictures["sine"]
        + "<p>Проведём построения, как показано на рисунке. Угол между сторонами правильного шестиугольника равен 120°. Треугольник ABC равнобедренный; BH — его высота, медиана и биссектриса:</p>"
        + line("AH=HC")
        + line(r"\angle CBH=\frac{120^{\circ}}{2}=60^{\circ}")
        + "<p>Из прямоугольного треугольника CBH найдём половину AC:</p>"
        + line(r"HC=BC\sin60^{\circ}")
        + line(r"HC=" + bracket(side) + r"\cdot\frac{\sqrt{3}}{2}=" + value(m.answer))
        + "<p>Длина AC равна диаметру вписанной окружности. Поэтому:</p>"
        + line(r"r=\frac{AC}{2}=HC=" + value(m.answer))
    )


def render(m, pictures):
    if m.mode.startswith("rhombus_"):
        return _rhombus(m, pictures)
    if m.mode == "hexagon_side":
        return _hexagon_side(m, pictures)
    return solution_section("Решение", _hexagon_cosine(m, pictures)) + solution_section(
        "Приведем другое решение",
        _hexagon_pythagoras(m, pictures) + _hexagon_sine(m, pictures),
    )
