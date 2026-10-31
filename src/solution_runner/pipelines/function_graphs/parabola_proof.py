"""Preserve all parent methods and distinguish the visible A from the other B."""

import sympy as sp

from ..calculus.common import X
from ..probability.common import line
from ..word_problems.math_common import fraction as frac
from ..word_problems.math_common import primitive
from ..word_problems.motion_chase_proof import section
from .hyperbola import latex as n
from .parabola_questions import A, C
from .parabola_system_proof import system
from .parabola_vertex_proof import vertex


def evaluate(a):
    p = sp.Poly(a.expression, X)
    aa, bb, cc = (p.nth(i) for i in (2, 1, 0))
    t = a.question.target
    html = "<p>Подставим запрошенный аргумент в найденную формулу:</p>"
    html += line(
        "f("
        + n(t)
        + ")=("
        + n(aa)
        + r")\cdot("
        + n(t)
        + ")^2+("
        + n(bb)
        + r")\cdot("
        + n(t)
        + ")+("
        + n(cc)
        + ")"
    )
    return html + line(
        "f("
        + n(t)
        + ")=("
        + n(aa * t**2)
        + ")+("
        + n(bb * t)
        + ")+("
        + n(cc)
        + ")="
        + n(a.result)
    )


def intersections(a):
    p = sp.Poly(primitive(a.question.given - a.expression, (X,)), X)
    aa, bb, cc = (p.nth(i) for i in (2, 1, 0))
    d = bb**2 - 4 * aa * cc
    html = "<p>В точках пересечения значения функций равны. Составим и решим квадратное уравнение:</p>"
    html += line(sp.latex(a.question.given) + "=" + sp.latex(a.expression))
    html += line(sp.latex(p.as_expr()) + "=0")
    html += line(
        "D=(" + n(bb) + ")^2-4\\cdot(" + n(aa) + r")\cdot(" + n(cc) + ")=" + n(d)
    )
    html += line(
        "x="
        + frac("-(" + n(bb) + r")\pm\sqrt{" + n(d) + "}", "2\\cdot(" + n(aa) + ")")
        + r"\in\left\{"
        + ";".join(n(r) for r in a.roots)
        + r"\right\}"
    )
    html += "<p>На рисунке отмечена точка A. Соответствующий ей корень известен по её абсциссе, поэтому второй корень относится к B:</p>"
    html += line("x_A=" + n(a.visible_a) + r",\qquad x_B=" + n(a.root))
    if a.question.kind == "intersection_y":
        aa, bb, cc = (sp.Poly(a.expression, X).nth(i) for i in (2, 1, 0))
        html += (
            "<p>Найдём ординату B подстановкой её абсциссы в любую из двух функций:</p>"
        )
        html += line(
            "y_B=g("
            + n(a.root)
            + ")=("
            + n(aa)
            + r")\cdot("
            + n(a.root)
            + ")^2+("
            + n(bb)
            + r")\cdot("
            + n(a.root)
            + ")+("
            + n(cc)
            + ")="
            + n(a.result)
        )
    return html


def given_intro(a):
    colors = {"#143B8F": "тёмно-синим", "#007EA5": "бирюзовым"}
    other = next(c for c in colors if c != a.curve["color"])
    html = "<p>По заданной формуле найдём пересечение графика f с осью ординат:</p>"
    html += line("f(0)=" + n(a.question.given.subs(X, 0)))
    return (
        html
        + f"<p>В данной схеме f соответствует графику, отмеченному {colors[other]} цветом, а g — графику, отмеченному {colors[a.curve['color']]} цветом. Восстановим формулу g.</p>"
    )


def proof(a):
    q = a.question
    if q.kind != "value":
        first = given_intro(a)
        algebra = system(a, "g") + intersections(a)
        if q.kind == "intersection_y":
            return section(
                first + vertex(a, "g", standard=True) + intersections(a), "Решение"
            ) + section(algebra, "Приведем другое решение.")
        return first + algebra
    algebra = system(a, "f") + evaluate(a)
    if A in q.fixed or C in q.fixed:
        return algebra
    geometric = vertex(a, "f")
    if q.whole:
        return geometric
    return section(geometric, "Решение") + section(algebra, "Приведем другое решение.")
