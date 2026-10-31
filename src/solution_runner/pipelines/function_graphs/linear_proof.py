"""Parent slope ratios, two-point systems and slope-based intersection proofs."""

import sympy as sp

from ..probability.common import line
from ..word_problems.math_common import fraction as frac
from ..word_problems.math_common import number as decimal
from ..word_problems.motion_chase_proof import section
from .hyperbola import latex as n


def par(value):
    return "(" + n(value) + ")"


def expression(one, scale=1):
    x = sp.Symbol("x")
    return sp.latex(
        sp.Rational(scale * one.slope) * x + sp.Rational(scale * one.intercept)
    )


def point(p):
    return "(" + n(p[0]) + ";" + n(p[1]) + ")"


def slope(one, symbol="k"):
    p, q = sorted(one.points)
    return line(
        symbol
        + "="
        + frac(r"\Delta y", r"\Delta x")
        + "="
        + frac(n(q[1]) + "-" + par(p[1]), n(q[0]) + "-" + par(p[0]))
        + "="
        + n(one.slope)
    )


def intercept(one, reference, symbol="b"):
    x, y = reference
    return line(
        symbol
        + "="
        + n(y)
        + "-"
        + par(one.slope)
        + r"\cdot"
        + par(x)
        + "="
        + n(one.intercept)
    )


def value_ratio(a):
    one, target = a.lines[0], a.target
    x, y = next(p for p in one.points if p[0] != target)
    asked = "f(" + n(target) + ")"
    delta = x - target
    html = (
        "<p>Из графика найдём угловой коэффициент прямой: он равен отношению приращения функции к приращению аргумента.</p>"
        + slope(one)
    )
    html += "<p>Для той же прямой это отношение одинаково на любом участке. Используем отмеченную точку и запрошенный аргумент:</p>"
    html += line("k=" + frac("f(" + n(x) + ")-" + asked, n(x) + "-" + par(target)))
    html += line(frac(n(y) + "-" + asked, n(delta)) + "=" + n(one.slope))
    html += line(
        n(y)
        + "-"
        + asked
        + "="
        + par(one.slope)
        + r"\cdot"
        + par(delta)
        + "="
        + n(one.slope * delta)
    )
    return html + line(
        asked + "=" + n(y) + "-" + par(one.slope * delta) + "=" + n(a.result)
    )


def value_formula(a):
    one = a.lines[0]
    html = (
        "<p>Для линейной функции угловой коэффициент определяется двумя отмеченными точками. Затем подставим одну из них, чтобы найти свободный член:</p>"
        + slope(one)
    )
    html += intercept(one, one.points[-1])
    html += line("f(x)=" + expression(one))
    html += "<p>Подставим требуемый аргумент в найденную формулу:</p>"
    return html + line(
        "f("
        + n(a.target)
        + ")="
        + par(one.slope)
        + r"\cdot"
        + par(a.target)
        + "+"
        + par(one.intercept)
        + "="
        + n(a.result)
    )


def inverse(a):
    one, target = a.lines[0], a.target
    p, q = one.points
    html = "<p>По рисунку определим значения функции в двух отмеченных точках:</p>"
    html += line(
        "f(" + n(p[0]) + ")=" + n(p[1]) + r",\quad f(" + n(q[0]) + ")=" + n(q[1])
    )
    html += "<p>Подставим их в формулу f(x)=kx+b и решим систему:</p>"
    html += line(
        r"\begin{cases}"
        + n(p[1])
        + "=k\\cdot"
        + par(p[0])
        + r"+b,\\"
        + n(q[1])
        + "=k\\cdot"
        + par(q[0])
        + r"+b.\end{cases}"
    )
    html += "<p>Вычитая первое уравнение из второго, найдём k, затем восстановим b:</p>"
    html += line("k=" + frac(n(q[1] - p[1]), n(q[0] - p[0])) + "=" + n(one.slope))
    html += intercept(one, p)
    html += line("f(x)=" + expression(one))
    html += "<p>Решим уравнение для указанного значения функции:</p>"
    if decimal(target) != n(target):
        html += line("f(x)=" + decimal(target) + "=" + n(target))
    html += line(expression(one) + "=" + n(target))
    scale = int(
        sp.ilcm(one.slope.denominator, one.intercept.denominator, target.denominator)
    )
    html += "<p>Умножим уравнение на общий знаменатель и перенесём свободный член вправо:</p>"
    html += line(expression(one, scale) + "=" + n(scale * target))
    html += line(n(scale * one.slope) + "x=" + n(scale * (target - one.intercept)))
    return html + line(
        "x="
        + frac(n(scale * (target - one.intercept)), n(scale * one.slope))
        + "="
        + n(a.result)
    )


def intersection(a):
    html = "<p>Уравнение прямой имеет вид y=kx+b. Угловой коэффициент — тангенс угла наклона прямой к положительному направлению оси абсцисс. Найдём его как отношение приращений, а свободный член — подстановкой отмеченной точки.</p>"
    colors = {"#143B8F": "тёмно-синим", "#007EA5": "бирюзовым"}
    for index, one in enumerate(a.lines, 1):
        p, q = sorted(one.points)
        html += f"<p>Прямая, отмеченная {colors[one.color]} цветом, проходит через точки {point(p)} и {point(q)}. Найдём её коэффициенты:</p>"
        html += slope(one, "k_" + str(index))
        html += intercept(one, one.points[0], "b_" + str(index))
        html += line("y=" + expression(one))
    first, second = a.lines
    html += "<p>В точке пересечения значения функций равны. Найдём её абсциссу:</p>"
    html += line(expression(first) + "=" + expression(second))
    html += line(
        par(first.slope - second.slope) + "x=" + n(second.intercept - first.intercept)
    )
    x, y = a.intersection
    html += line(
        "x="
        + frac(n(second.intercept - first.intercept), n(first.slope - second.slope))
        + "="
        + n(x)
    )
    if a.kind == "intersection_y":
        html += "<p>Подставим найденную абсциссу в уравнение любой из прямых, чтобы найти ординату:</p>"
        html += line(
            "y="
            + par(first.slope)
            + r"\cdot"
            + par(x)
            + "+"
            + par(first.intercept)
            + "="
            + n(y)
        )
    return html


def proof(a):
    if a.kind == "value":
        return section(value_ratio(a), "Решение") + section(
            value_formula(a), "Приведем другое решение."
        )
    return inverse(a) if a.kind == "argument" else intersection(a)
