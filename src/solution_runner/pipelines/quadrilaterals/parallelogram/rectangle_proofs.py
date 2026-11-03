"""Expand the six reviewed rectangle methods, including both parent remarks."""

import sympy as sp

from ...probability.common import line
from ...triangles.right.altitude_methods import solution_section
from ...word_problems.math_common import number


def value(x):
    x = sp.simplify(x)
    return number(x) if x.is_Rational else sp.latex(x)


def bracket(x):
    return r"\left(" + value(x) + r"\right)"


def _square(m):
    d = m.given[0]
    return (
        "<p>Площадь квадрата равна половине произведения длин его диагоналей. Диагонали квадрата равны, поэтому обозначим обе их длины данным числом:</p>"
        + line("AC=BD=" + value(d))
        + line(r"S=\frac{AC\cdot BD}{2}")
        + "<p>Подставим длины диагоналей и вычислим площадь:</p>"
        + line(r"S=\frac{" + value(d) + r"\cdot " + value(d) + "}{2}")
        + line(r"S=\frac{" + value(d**2) + "}{2}")
        + line("S=" + value(m.answer))
    )


def _difference(m):
    area, gap = m.given
    disc = gap**2 + 4 * area
    return (
        "<p>Площадь прямоугольника равна произведению его длины на ширину. Пусть меньшая сторона равна a, тогда большая сторона равна b:</p>"
        + line("S=ab=" + value(area))
        + line("b=a+" + value(gap))
        + "<p>Подставим выражение для большей стороны в формулу площади и решим квадратное уравнение:</p>"
        + line("a(a+" + value(gap) + ")=" + value(area))
        + line("a^2+" + value(gap) + "a-" + value(area) + "=0")
        + line("D=" + bracket(gap) + r"^2+4\cdot " + value(area) + "=" + value(disc))
        + "<p>Длина стороны положительна, поэтому выбираем положительный корень. Затем найдём большую сторону:</p>"
        + line(
            r"a=\frac{-" + value(gap) + r"+\sqrt{" + value(disc) + "}}{2}=" + value(m.a)
        )
        + line("b=" + value(m.a) + "+" + value(gap) + "=" + value(m.answer))
    )


def _ratio(m):
    area, r, s = m.given
    scale = sp.simplify(m.a / r)
    first = "a" if r == 1 else value(r) + "a"
    second = "a" if s == 1 else value(s) + "a"
    return (
        "<p>Площадь прямоугольника равна произведению его длины на ширину. Периметр прямоугольника равен сумме длин всех его сторон. Выразим стороны согласно данному отношению через положительный общий множитель a:</p>"
        + line("S=(" + first + ")(" + second + ")")
        + line("S=" + value(r * s) + "a^2=" + value(area))
        + line(r"a^2=\frac{" + value(area) + "}{" + value(r * s) + "}")
        + line(
            r"a=\sqrt{\frac{" + value(area) + "}{" + value(r * s) + "}}=" + value(scale)
        )
        + "<p>Найдём обе стороны и сложим длины всех четырёх сторон прямоугольника:</p>"
        + line(first + "=" + value(r) + r"\cdot " + bracket(scale) + "=" + value(m.a))
        + line(second + "=" + value(s) + r"\cdot " + bracket(scale) + "=" + value(m.b))
        + line("P=2(" + first + "+" + second + ")")
        + line("P=2(" + value(m.a) + "+" + value(m.b) + ")=" + value(m.answer))
    )


def _side_rows(m):
    p, area = m.given
    total, disc = p / 2, p**2 / 4 - 4 * area
    givens = ["P=2(a+b)=" + value(p), "S=ab=" + value(area)]
    if m.mode == "side":
        givens.reverse()
    return (
        "".join(line(f) for f in givens)
        + line(r"a+b=\frac{" + value(p) + "}{2}=" + value(total))
        + line("b(" + value(total) + "-b)=" + value(area))
        + line("b^2-" + value(total) + "b+" + value(area) + "=0")
        + line("D=" + bracket(total) + r"^2-4\cdot " + value(area) + "=" + value(disc))
        + line(
            r"b_1=\frac{"
            + value(total)
            + r"-\sqrt{"
            + value(disc)
            + "}}{2}="
            + value(m.a)
            + r",\quad b_2=\frac{"
            + value(total)
            + r"+\sqrt{"
            + value(disc)
            + "}}{2}="
            + value(m.b)
        )
    )


def _side(m):
    total = m.given[0] / 2
    return (
        "<p>Площадь прямоугольника равна произведению его длины на ширину. Периметр прямоугольника равен сумме длин всех сторон. Пусть стороны равны a и b. Выразим a через b и подставим в формулу площади:</p>"
        + _side_rows(m)
        + "<p>Два корня задают длины сторон: при выборе одного корня вторая сторона равна другому. Назовём меньшую сторону a и найдём большую сторону b:</p>"
        + line("a=" + value(m.a))
        + line("b=" + value(total) + "-" + bracket(m.a) + "=" + value(m.answer))
    )


def _area(m):
    p, d = m.given
    total = p / 2
    return (
        "<p>Периметр прямоугольника равен сумме длин его сторон. Площадь прямоугольника равна произведению его длины на ширину. Пусть стороны равны a и b:</p>"
        + line("P=2(a+b)=" + value(p))
        + line(r"a+b=\frac{" + value(p) + "}{2}=" + value(total))
        + "<p>Диагональ делит прямоугольник на два прямоугольных треугольника. По теореме Пифагора запишем сумму квадратов сторон. Затем раскроем квадрат суммы, чтобы найти произведение сторон:</p>"
        + line("a^2+b^2=" + bracket(d) + "^2=" + value(d**2))
        + line("a^2+2ab+b^2=(a+b)^2")
        + line("2ab=(a+b)^2-(a^2+b^2)")
        + line("2ab=" + bracket(total) + "^2-" + bracket(d) + "^2")
        + line("2ab=" + value(total**2 - d**2))
        + line(r"S=ab=\frac{" + value(total**2 - d**2) + "}{2}=" + value(m.answer))
    )


def _diagonal(m):
    p, area = m.given
    total, disc = p / 2, p**2 / 4 - 4 * area
    squared = sp.simplify(m.a**2 + m.b**2)
    expansion = (
        line(
            "a^2+b^2="
            + bracket(sp.expand(m.a**2))
            + "+"
            + bracket(sp.expand(m.b**2))
            + "="
            + value(squared)
        )
        if not (m.a.is_Rational and m.b.is_Rational)
        else ""
    )
    return (
        "<p>Периметр прямоугольника равен сумме длин его сторон. Площадь прямоугольника равна их произведению. Пусть длины сторон равны a и b. Решим систему, выразив a через b:</p>"
        + _side_rows(m)
        + "<p>Таким образом, стороны прямоугольника равны найденным корням. Диагональ разбивает прямоугольник на два прямоугольных треугольника, в которых она является гипотенузой. Пусть её длина равна c. По теореме Пифагора:</p>"
        + line("c^2=a^2+b^2")
        + expansion
        + line(
            r"c=\sqrt{"
            + bracket(m.a)
            + "^2+"
            + bracket(m.b)
            + r"^2}=\sqrt{"
            + value(squared)
            + "}="
            + value(m.answer)
        )
        + "<p><b>Примечание 1.</b></p><p>Можно заметить, что система является системой Виета. Следовательно, её решения — корни квадратного уравнения:</p>"
        + line("a+b=" + value(total) + r",\quad ab=" + value(area))
        + line("t^2-" + value(total) + "t+" + value(area) + "=0")
        + line("D=" + value(disc))
        + line(
            r"t_1=\frac{"
            + value(total)
            + r"-\sqrt{"
            + value(disc)
            + "}}{2}="
            + value(m.a)
            + r",\quad t_2=\frac{"
            + value(total)
            + r"+\sqrt{"
            + value(disc)
            + "}}{2}="
            + value(m.b)
        )
        + line("c^2=t_1^2+t_2^2=" + value(squared))
        + line(r"c=\sqrt{" + value(squared) + "}=" + value(m.answer))
        + "<p><b>Примечание 2.</b></p><p>Можно было и вовсе не решать систему уравнений: используем квадрат суммы сторон и их произведение:</p>"
        + line("c^2=a^2+b^2")
        + line("a^2+b^2=(a+b)^2-2ab")
        + line("c^2=" + bracket(total) + r"^2-2\cdot " + value(area))
        + line("c^2=" + value(total**2) + "-" + value(2 * area))
        + line("c^2=" + value(squared))
        + line(r"c=\sqrt{" + value(squared) + "}=" + value(m.answer))
    )


def render(m):
    body = {
        "square": _square,
        "difference": _difference,
        "ratio": _ratio,
        "side": _side,
        "area": _area,
        "diagonal": _diagonal,
    }[m.mode](m)
    return solution_section("Решение", body)
