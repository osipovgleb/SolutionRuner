"""Two-coefficient systems and the parent's subtraction of three function values."""

from itertools import combinations

import sympy as sp

from ..calculus.common import X
from ..core.errors import ContentPlanError
from ..probability.common import line
from ..word_problems.math_common import fraction as frac
from .hyperbola import latex as n
from .parabola_questions import PARAMETERS, A


def basis(a):
    fixed = a.question.fixed if a.question.kind == "value" else {}
    unknown = [s for s in PARAMETERS if s not in fixed]
    points = (
        a.curve["marked_points"]
        if len(a.curve["marked_points"]) >= len(unknown)
        else a.curve["points"]
    )
    for chosen in combinations(
        sorted(tuple(map(sp.Rational, p)) for p in points), len(unknown)
    ):
        matrix = sp.Matrix(
            [
                [
                    sp.diff(PARAMETERS[0] * x**2 + PARAMETERS[1] * x + PARAMETERS[2], s)
                    for s in unknown
                ]
                for x, y in chosen
            ]
        )
        if matrix.det() != 0:
            return chosen
    raise ContentPlanError(
        "the graph points must give an independent coefficient system"
    )


def parameters(a):
    p = sp.Poly(a.expression, X)
    return {s: p.nth(i) for s, i in zip(PARAMETERS, (2, 1, 0), strict=True)}


def eliminate(rows, names, values):
    (alpha, beta, first), (gamma, delta, second) = rows
    det, rhs = alpha * delta - gamma * beta, first * delta - second * beta
    u, v = names
    if det == 0:
        raise ContentPlanError("the coefficient elimination must be nonsingular")
    html = "<p>Исключим вторую неизвестную, умножив уравнения на подходящие коэффициенты и вычтя их:</p>"
    html += line(n(det) + str(u) + "=" + n(rhs))
    html += line(str(u) + "=" + frac(n(rhs), n(det)) + "=" + n(values[u]))
    row = rows[0] if beta else rows[1]
    html += "<p>Подставим найденное значение в одно из уравнений:</p>"
    html += line(
        str(v)
        + "="
        + frac(
            n(row[2]) + "-(" + n(row[0]) + r")\cdot(" + n(values[u]) + ")", n(row[1])
        )
        + "="
        + n(values[v])
    )
    return html


def substitute(rows, names, values):
    (alpha, beta, first), (gamma, delta, second) = rows
    u, v = names
    replacement = (first - alpha * u) / beta
    coefficient = gamma - delta * alpha / beta
    right = second - delta * first / beta
    html = "<p>Выразим свободный член из первого уравнения и подставим во второе:</p>"
    html += line(str(v) + "=" + sp.latex(replacement))
    html += line(
        n(gamma)
        + str(u)
        + "+("
        + n(delta)
        + r")\cdot\left("
        + sp.latex(replacement)
        + r"\right)="
        + n(second)
    )
    html += line(n(coefficient) + str(u) + "=" + n(right))
    html += line(str(u) + "=" + frac(n(right), n(coefficient)) + "=" + n(values[u]))
    html += line(
        str(v)
        + "="
        + frac(n(first) + "-(" + n(alpha) + r")\cdot(" + n(values[u]) + ")", n(beta))
        + "="
        + n(values[v])
    )
    return html


def system(a, name):
    points = basis(a)
    fixed = a.question.fixed if a.question.kind == "value" else {}
    unknown = [s for s in PARAMETERS if s not in fixed]
    values = parameters(a)
    html = "<p>Из рисунка определим значения функции в отмеченных узлах сетки:</p>"
    html += line(r",\quad ".join(name + "(" + n(x) + ")=" + n(y) for x, y in points))
    if len(unknown) == 2:
        rows = []
        symbolic = PARAMETERS[0] * X**2 + PARAMETERS[1] * X + PARAMETERS[2]
        template = symbolic.subs(fixed)
        for x, y in points:
            value = template.subs(X, x)
            constant = value.subs({s: 0 for s in unknown})
            rows.append(tuple(sp.diff(value, s) for s in unknown) + (y - constant,))
        html += "<p>Подставим координаты в заданную формулу и перенесём известные слагаемые вправо:</p>"
        html += line(
            r"\begin{cases}"
            + r",\\".join(
                sp.latex(row[0] * unknown[0] + row[1] * unknown[1]) + "=" + n(row[2])
                for row in rows
            )
            + r".\end{cases}"
        )
        html += (
            substitute(rows, unknown, values)
            if A in fixed
            else eliminate(rows, unknown, values)
        )
    else:
        p, q, r = points
        rows = [
            (left[0] ** 2 - right[0] ** 2, left[0] - right[0], left[1] - right[1])
            for left, right in ((p, q), (q, r))
        ]
        html += "<p>Вычтем значения функции попарно: свободный член c сократится.</p>"
        for (left, right), row in zip(((p, q), (q, r)), rows, strict=True):
            html += line(
                name
                + "("
                + n(left[0])
                + ")-"
                + name
                + "("
                + n(right[0])
                + ")="
                + n(row[0])
                + "a+("
                + n(row[1])
                + ")b="
                + n(row[2])
            )
        html += eliminate(rows, PARAMETERS[:2], values)
        x, y = p
        html += "<p>Восстановим свободный член по одной из точек:</p>"
        html += line(
            "c="
            + n(y)
            + "-("
            + n(values[PARAMETERS[0]])
            + r")\cdot("
            + n(x)
            + ")^2-("
            + n(values[PARAMETERS[1]])
            + r")\cdot("
            + n(x)
            + ")="
            + n(values[PARAMETERS[2]])
        )
    return html + line(name + "(x)=" + sp.latex(a.expression))
