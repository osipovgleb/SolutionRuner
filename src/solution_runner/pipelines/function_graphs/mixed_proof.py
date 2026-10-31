"""Solve original curve/line equations, reject negative roots and identify A/B."""

import sympy as sp

from ..calculus.common import X
from ..probability.common import line
from ..word_problems.motion_chase_proof import section
from .hyperbola import latex as n
from .mixed_coefficients import curve, linear
from .mixed_models import T
from .parabola_proof import quadratic_steps


def equations(a):
    q = a.question
    linear_expression = a.line.slope * X + a.line.intercept
    html = "<p>В точке пересечения значения функций равны. Составим уравнение:</p>"
    html += line(sp.latex(a.expression) + "=" + sp.latex(linear_expression))
    if q.curve_kind == "root":
        coefficient = sp.simplify(a.expression / sp.sqrt(X))
        html += "<p>Область определения требует неотрицательной абсциссы. Введём неотрицательный квадратный корень как новую переменную и решим квадратное уравнение:</p>"
        html += line(r"x\geq0,\qquad t=\sqrt{x}\geq0,\qquad x=t^2")
        html += quadratic_steps(
            a.line.slope * T**2 - coefficient * T + a.line.intercept, T, a.t_roots
        )
        admissible = [t for t in a.t_roots if t >= 0]
        html += (
            "<p>Отрицательное значение t не может быть квадратным корнем. Оставим допустимые значения и вернёмся к x:</p>"
            if any(t < 0 for t in a.t_roots)
            else "<p>Все найденные значения t неотрицательны. Вернёмся к x:</p>"
        )
        html += line(
            r"t\in\left\{" + (";".join(n(t) for t in admissible)) + r"\right\}"
        )
        html += line(
            r"x=t^2\in\left\{" + (";".join(n(r) for r in a.roots)) + r"\right\}"
        )
        return html
    equation = linear_expression - a.expression
    if q.curve_kind == "reciprocal":
        html += (
            "<p>При x ≠ 0 умножение обеих частей на x сохраняет решения:</p>"
            + line(r"x\ne0")
        )
        equation = sp.cancel(equation * X)
    return html + quadratic_steps(equation, X, a.roots)


def identify(a):
    q = a.question
    html = ""
    if q.count == 2:
        x, y = map(sp.Rational, a.entry["visible_a"])
        html = "<p>На рисунке отмечена точка A. Её абсцисса соответствует одному из найденных корней, поэтому второй корень относится к B:</p>"
        html += line(
            "A=("
            + n(x)
            + ";"
            + n(y)
            + r"),\qquad x_A="
            + n(x)
            + r",\qquad x_B="
            + n(a.root)
        )
    else:
        html = "<p>Уравнение имеет одно допустимое решение, поэтому оно задаёт абсциссу точки A:</p>"
        html += line("x_A=" + n(a.root))
    if q.coordinate == "y" or q.curve_kind == "root":
        html += "<p>Найдём ординату подстановкой абсциссы в уравнение прямой:</p>"
        html += line(
            "y_"
            + q.letter
            + "="
            + q.line_name
            + "("
            + n(a.root)
            + ")=("
            + n(a.line.slope)
            + r")\cdot("
            + n(a.root)
            + ")+("
            + n(a.line.intercept)
            + ")"
        )
        html += line(
            "y_"
            + q.letter
            + "=("
            + n(a.line.slope * a.root)
            + ")+("
            + n(a.line.intercept)
            + ")="
            + n(a.ordinate)
        )
    return html


def proof(a):
    return section(curve(a) + linear(a) + equations(a) + identify(a), "Решение")
