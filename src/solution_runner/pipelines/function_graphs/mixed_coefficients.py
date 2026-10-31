"""Reuse the quadratic subtraction and root coefficient methods of the parents."""

from itertools import combinations

import sympy as sp

from ..calculus.common import X
from ..core.errors import ContentPlanError
from ..probability.common import line
from .hyperbola import latex as n
from .parabola_models import Analysis as QuadraticAnalysis
from .parabola_questions import Question as QuadraticQuestion
from .parabola_system_proof import system
from .root_graph import coefficient_proof


def symmetry(a):
    points = [tuple(map(sp.Rational, p)) for p in a.entry["curve_points"]]
    pair = next((p for p in combinations(points, 2) if p[0][1] == p[1][1]), None)
    if not pair or (0, 0) not in points:
        raise ContentPlanError(
            "the parent axis method needs symmetric graph readings and the origin"
        )
    (x1, y), (x2, _) = pair
    h = (x1 + x2) / 2
    p = sp.Poly(a.expression, X)
    aa, bb, cc = (p.nth(i) for i in (2, 1, 0))
    if cc != 0 or -bb / (2 * aa) != h:
        raise ContentPlanError(
            "the symmetry axis must agree with all reconstructed points"
        )
    probes = [(x, y) for x, y in points if x > 0 and x * x - 2 * h * x != 0]
    if not probes:
        raise ContentPlanError(
            "one nonzero graph value is needed after finding the symmetry axis"
        )
    x, y = min(probes)
    factor = x * x - 2 * h * x
    html = "<p>По рисунку найдём две точки параболы с одинаковой ординатой. Ось симметрии проходит посередине между их абсциссами:</p>"
    html += line("f(" + n(x1) + ")=f(" + n(x2) + ")=" + n(pair[0][1]))
    html += line(r"x_0=\frac{" + n(x1) + "+(" + n(x2) + ")}{2}=" + n(h))
    html += "<p>Парабола проходит через начало координат, поэтому свободный член равен нулю. Используем формулу абсциссы вершины и ещё одну точку:</p>"
    html += line("f(0)=0,\\qquad c=0")
    html += line(r"x_0=-\frac{b}{2a}=" + n(h) + r",\qquad b=(" + n(-2 * h) + ")a")
    html += line(
        "f("
        + n(x)
        + ")="
        + n(y)
        + r",\qquad a\cdot("
        + n(x)
        + ")^2+("
        + n(-2 * h)
        + r")a\cdot("
        + n(x)
        + ")="
        + n(y)
    )
    html += line("(" + n(factor) + r")a=" + n(y) + r",\qquad a=" + n(aa))
    html += line("b=(" + n(-2 * h) + r")\cdot(" + n(aa) + ")=" + n(bb))
    return html + line("f(x)=" + sp.latex(a.expression))


def curve(a):
    q = a.question
    if q.curve_kind == "parabola":
        if q.line_origin:
            return symmetry(a)
        adapter = QuadraticAnalysis(
            QuadraticQuestion("intersection_x", {}),
            {
                "marked_points": a.entry["curve_points"],
                "points": a.entry["curve_points"],
            },
            a.expression,
        )
        return system(adapter, q.curve_name)
    point = next(
        tuple(map(sp.Rational, p)) for p in a.entry["curve_points"] if p[0] != 0
    )
    x, y = point
    if q.curve_kind == "root":
        coefficient = sp.simplify(a.expression / sp.sqrt(X))
        return coefficient_proof(point, coefficient, name="a") + line(
            "f(x)=" + sp.latex(a.expression)
        )
    coefficient = sp.simplify(a.expression * X)
    html = "<p>По графику определим значение обратной пропорциональности в отмеченной точке и найдём коэффициент k:</p>"
    html += line("f(" + n(x) + ")=" + n(y) + r",\qquad \frac{k}{" + n(x) + "}=" + n(y))
    html += line("k=(" + n(x) + r")\cdot(" + n(y) + ")=" + n(coefficient))
    return html + line("f(x)=" + sp.latex(a.expression))


def linear(a):
    q = a.question
    if q.known_line is not None:
        return ""
    (x1, y1), (x2, y2) = a.line.points
    slope, intercept = a.line.slope, a.line.intercept
    k, b = q.line_symbols
    if q.curve_kind == "parabola" and not q.line_origin:
        html = "<p>Прямая проходит через две отмеченные точки. Составим и решим систему для её коэффициентов:</p>"
        html += line(
            r"\begin{cases}"
            + n(y1)
            + "=("
            + n(x1)
            + ")"
            + k
            + "+"
            + b
            + r",\\"
            + n(y2)
            + "=("
            + n(x2)
            + ")"
            + k
            + "+"
            + b
            + r".\end{cases}"
        )
        html += line(
            "("
            + n(x2 - x1)
            + ")"
            + k
            + "="
            + n(y2 - y1)
            + r",\qquad "
            + k
            + "="
            + n(slope)
        )
    else:
        html = "<p>Угловой коэффициент прямой равен тангенсу угла её наклона к положительному направлению оси абсцисс. Найдём его по двум точкам:</p>"
        html += line(
            k
            + r"=\frac{\Delta y}{\Delta x}=\frac{"
            + n(y2)
            + "-("
            + n(y1)
            + ")}{"
            + n(x2)
            + "-("
            + n(x1)
            + ")}="
            + n(slope)
        )
    if not q.line_origin:
        x, y = next((p for p in a.line.points if p[0] == 0), a.line.points[-1])
        html += "<p>Подставим координаты точки прямой и найдём свободный член:</p>"
        html += line(n(y) + "=(" + n(slope) + r")\cdot(" + n(x) + ")+" + b)
        html += line(
            b + "=" + n(y) + "-(" + n(slope) + r")\cdot(" + n(x) + ")=" + n(intercept)
        )
    return html + line(q.line_name + "(x)=" + sp.latex(slope * X + intercept))
