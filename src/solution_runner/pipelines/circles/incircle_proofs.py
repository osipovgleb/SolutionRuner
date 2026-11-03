"""Preserve area, right-triangle, Heron and equal-tangent parent methods."""

import sympy as sp

from ..probability.common import line
from ..quadrilaterals.parallelogram.rectangle_proofs import bracket, value
from ..triangles.right.altitude_methods import solution_section
from . import incircle_polygon_proofs, incircle_regular_proofs


def _area(m):
    perimeter, radius = m.given if m.mode == "triangle_area" else m.given[::-1]
    p = perimeter / 2
    intro = (
        "Площадь треугольника равна произведению его полупериметра p на радиус вписанной окружности r."
        if m.mode == "triangle_area"
        else "Радиус окружности, вписанной в многоугольник, равен отношению его площади к полупериметру. Пусть площадь равна S, полупериметр — p, радиус — r."
    )
    return (
        "<p>"
        + intro
        + " Найдём полупериметр и подставим данные:</p>"
        + line(r"p=\frac{P}{2}")
        + line(r"p=\frac{" + value(perimeter) + "}{2}=" + value(p))
        + line("S=pr")
        + line("S=" + bracket(p) + r"\cdot " + bracket(radius))
        + line("S=" + value(m.answer))
    )


def _perimeter(m):
    area, radius = m.given
    return (
        "<p>Из формулы S=pr, где p — полупериметр, выразим сначала полупериметр, затем периметр треугольника:</p>"
        + line("S=pr")
        + line(r"p=\frac{S}{r}")
        + line(
            r"p=\frac{"
            + value(area)
            + "}{"
            + value(radius)
            + "}="
            + value(area / radius)
        )
        + line(r"P=2p=\frac{2S}{r}")
        + line(
            r"P=\frac{2\cdot "
            + bracket(area)
            + "}{"
            + value(radius)
            + "}="
            + value(m.answer)
        )
    )


def _isosceles_right(m):
    a = m.given[0]
    first = (
        "<p>Радиус вписанной в прямоугольный треугольник окружности равен полуразности суммы катетов и гипотенузы. Оба катета равны a, поэтому по теореме Пифагора:</p>"
        + line(r"c=\sqrt{a^2+a^2}=a\sqrt{2}")
        + line(r"r=\frac{a+a-c}{2}")
        + line(r"r=\frac{2a-a\sqrt{2}}{2}=\frac{a(2-\sqrt{2})}{2}")
        + line(r"r=\frac{" + bracket(a) + r"(2-\sqrt{2})}{2}=" + value(m.answer))
    )
    second = (
        "<p>Радиус вписанной окружности равен отношению удвоенной площади к периметру. Для равных катетов a площадь равна половине квадрата катета, а гипотенуза равна a√2:</p>"
        + line(r"S=\frac{a^2}{2}")
        + line(r"P=2a+a\sqrt{2}")
        + line(r"r=\frac{2S}{P}=\frac{a^2}{2a+a\sqrt{2}}")
        + line(r"r=\frac{a^2}{a(2+\sqrt{2})}=\frac{a}{2+\sqrt{2}}")
        + line(r"r=\frac{" + value(a) + r"}{2+\sqrt{2}}=" + value(m.answer))
    )
    return first, second


def _right(m):
    a, b = m.given[:2]
    c = sp.sqrt(a * a + b * b)
    first = (
        "<p>Радиус вписанной окружности прямоугольного треугольника равен полуразности суммы катетов и гипотенузы. Гипотенузу найдём по теореме Пифагора:</p>"
        + line(r"AB=\sqrt{AC^2+BC^2}")
        + line(r"AB=\sqrt{" + bracket(a) + "^2+" + bracket(b) + "^2}=" + value(c))
        + line(r"r=\frac{AC+BC-AB}{2}")
        + line(r"r=\frac{" + value(a + b) + "-" + value(c) + "}{2}=" + value(m.answer))
    )
    second = (
        "<p>Найдём гипотенузу по теореме Пифагора. Затем выразим радиус через площадь и периметр:</p>"
        + line(r"AB=\sqrt{AC^2+BC^2}=" + value(c))
        + line(r"S_{ABC}=\frac{1}{2}AC\cdot BC")
        + line(r"S_{ABC}=\frac{1}{2}P_{ABC}r")
        + line(r"r=\frac{AC\cdot BC}{P_{ABC}}")
        + line(
            r"r=\frac{"
            + bracket(a)
            + r"\cdot "
            + bracket(b)
            + "}{"
            + value(a + b + c)
            + "}="
            + value(m.answer)
        )
    )
    return first, second


def _isosceles(m):
    leg, base = m.given
    p = leg + base / 2
    h = sp.sqrt(leg * leg - base * base / 4)
    area = base * h / 2
    heron = p * (p - leg) ** 2 * (p - base)
    first = (
        "<p>Радиус вписанной окружности равен отношению площади к полупериметру. Сначала найдём полупериметр, а для площади воспользуемся формулой Герона:</p>"
        + line(
            r"p=\frac{AB+BC+AC}{2}=\frac{2\cdot "
            + bracket(leg)
            + "+"
            + value(base)
            + "}{2}="
            + value(p)
        )
        + line(r"S=\sqrt{p(p-AB)(p-BC)(p-AC)}")
        + line(
            r"S=\sqrt{"
            + bracket(p)
            + r"\cdot "
            + bracket(p - leg)
            + r"\cdot "
            + bracket(p - leg)
            + r"\cdot "
            + bracket(p - base)
            + "}"
        )
        + line(r"S=\sqrt{" + value(heron) + "}=" + value(area))
        + line(
            r"r=\frac{S}{p}=\frac{"
            + value(area)
            + "}{"
            + value(p)
            + "}="
            + value(m.answer)
        )
    )
    second = (
        "<p>Для нахождения площади найдём высоту равнобедренного треугольника. Высота к основанию AC делит его пополам:</p>"
        + line(r"h=\sqrt{AB^2-\left(\frac{AC}{2}\right)^2}")
        + line(
            r"h=\sqrt{" + bracket(leg) + "^2-" + bracket(base / 2) + "^2}=" + value(h)
        )
        + line(r"S=\frac{AC\cdot h}{2}")
        + line(
            r"S=\frac{" + bracket(base) + r"\cdot " + bracket(h) + "}{2}=" + value(area)
        )
        + "<p>Разделим площадь на тот же полупериметр:</p>"
        + line(
            r"r=\frac{S}{p}=\frac{"
            + value(area)
            + "}{"
            + value(p)
            + "}="
            + value(m.answer)
        )
    )
    return first, second


def _tangent_parts(m):
    apex, lower = m.given
    leg = apex + lower
    return (
        "<p>Пусть H и K — точки касания со сторонами AC и CB. Прямоугольные треугольники HOC и KOC имеют общую гипотенузу OC и равные катеты OH и OK — радиусы окружности. Поэтому эти треугольники равны, а отрезки касательных из C равны:</p>"
        + line("HC=KC=" + value(lower))
        + "<p>Отрезок от вершины B до точки касания имеет данную первую длину. Найдём боковую сторону. В равнобедренном треугольнике точка касания с основанием лежит в его середине:</p>"
        + line("BC=BK+KC=" + value(apex) + "+" + value(lower) + "=" + value(leg))
        + line("AH=HC")
        + "<p>Сложим стороны треугольника, используя равенство боковых сторон и половин основания:</p>"
        + line(r"P_{ABC}=AB+BC+AH+HC=2BC+2HC")
        + line(
            r"P_{ABC}=2\cdot "
            + bracket(leg)
            + r"+2\cdot "
            + bracket(lower)
            + "="
            + value(m.answer)
        )
    )


def render(m, pictures):
    if m.mode in incircle_polygon_proofs.MODES:
        return incircle_polygon_proofs.render(m, pictures)
    if m.mode in incircle_regular_proofs.MODES:
        return incircle_regular_proofs.render(m, pictures)
    methods = {
        "polygon_area": _area,
        "triangle_area": _area,
        "triangle_perimeter": _perimeter,
        "isosceles_right_radius": _isosceles_right,
        "right_radius": _right,
        "isosceles_radius": _isosceles,
        "tangent_perimeter": _tangent_parts,
    }
    body = methods[m.mode](m)
    if isinstance(body, tuple):
        title = (
            "Приведём другое решение"
            if m.mode == "isosceles_right_radius"
            else "Альтернативное решение."
        )
        return solution_section("Решение", body[0]) + solution_section(title, body[1])
    return solution_section("Решение", pictures.get("detail", "") + body)
