"""Vertex form, including exact recovery when the vertex is between grid nodes."""

import sympy as sp

from ..calculus.common import X
from ..core.errors import ContentPlanError
from ..probability.common import line
from ..word_problems.math_common import fraction as frac
from .hyperbola import formula
from .hyperbola import latex as n
from .parabola_questions import B
from .parabola_system_proof import basis


def recover(a):
    if a.curve.get("vertex"):
        h, k = map(sp.Rational, a.curve["vertex"])
        marked = a.curve["marked_points"]
        points = (
            marked
            if a.question.kind == "value" and any(p[0] != h for p in marked)
            else marked + a.curve["points"]
        )
        x, y = min(
            (tuple(map(sp.Rational, p)) for p in points if p[0] != h),
            key=lambda p: abs(p[0] - h),
        )
        scale = (y - k) / (x - h) ** 2
        html = (
            "<p>По рисунку определим координаты вершины "
            + formula("(" + n(h) + ";" + n(k) + ")")
            + ". Запишем функцию в вершинной форме:</p>"
        )
        html += line("y=a(x-(" + n(h) + "))^2+(" + n(k) + ")")
        html += (
            "<p>Подставим ещё одну точку графика, чтобы определить коэффициент a:</p>"
        )
        html += line("a\\cdot(" + n(x) + "-(" + n(h) + "))^2+(" + n(k) + ")=" + n(y))
        html += line("a=" + frac(n(y - k), n((x - h) ** 2)) + "=" + n(scale))
        return scale, h, k, html
    points = basis(a)
    p, q = points[:2]
    m = (q[1] - p[1]) / (q[0] - p[0])
    html = "<p>Точная вершина здесь не отмечена в узле сетки. Найдём её координаты через наклоны хорд и затем используем вершинную форму.</p>"
    html += line("m_{12}=" + frac(n(q[1] - p[1]), n(q[0] - p[0])) + "=" + n(m))
    if B in a.question.fixed and a.question.kind == "value":
        b = a.question.fixed[B]
        scale = (m - b) / (p[0] + q[0])
        h = -b / (2 * scale)
        html += "<p>Для квадратичной функции наклон хорды равен a(x₁+x₂)+b. Коэффициент b известен по условию:</p>"
        html += line(
            "a=" + frac(n(m) + "-(" + n(b) + ")", n(p[0] + q[0])) + "=" + n(scale)
        )
        html += line(
            "h=" + frac("-(" + n(b) + ")", "2\\cdot(" + n(scale) + ")") + "=" + n(h)
        )
    else:
        r = points[2]
        other = (r[1] - q[1]) / (r[0] - q[0])
        scale = (other - m) / (r[0] - p[0])
        h = (p[0] + q[0] - m / scale) / 2
        html += line("m_{23}=" + frac(n(r[1] - q[1]), n(r[0] - q[0])) + "=" + n(other))
        html += "<p>В форме y=a(x−h)²+k вершина имеет координаты (h;k). Наклоны хорд равны a(x₁+x₂−2h) и a(x₂+x₃−2h). Их разность позволяет найти a, затем h:</p>"
        html += line(
            "a=" + frac(n(other) + "-(" + n(m) + ")", n(r[0] - p[0])) + "=" + n(scale)
        )
        html += line(
            "h=" + frac(n(p[0] + q[0]) + "-" + frac(n(m), n(scale)), "2") + "=" + n(h)
        )
    k = p[1] - scale * (p[0] - h) ** 2
    html += "<p>Подставим одну из точек и найдём ординату вершины:</p>"
    html += line(
        "k="
        + n(p[1])
        + "-("
        + n(scale)
        + r")\cdot("
        + n(p[0])
        + "-("
        + n(h)
        + "))^2="
        + n(k)
    )
    return scale, h, k, html


def vertex(a, name, *, standard=False):
    scale, h, k, html = recover(a)
    expression = scale * (X - h) ** 2 + k
    if sp.expand(expression - a.expression) != 0:
        raise ContentPlanError(
            "the vertex method must agree with the independently reconstructed polynomial"
        )
    html += line(name + "(x)=" + sp.latex(expression))
    if standard:
        html += "<p>Для стандартной формы b=−2ah. Свободный член равен значению при x=0:</p>"
        html += line(
            "b=-2\\cdot(" + n(scale) + r")\cdot(" + n(h) + ")=" + n(-2 * scale * h)
        )
        html += line(
            "c="
            + n(scale)
            + r"\cdot("
            + n(h)
            + ")^2+("
            + n(k)
            + ")="
            + n(scale * h**2 + k)
        )
        return html + line(name + "(x)=" + sp.latex(a.expression))
    target = a.question.target
    html += "<p>Вычислим значение функции при требуемом аргументе:</p>"
    html += line(
        name
        + "("
        + n(target)
        + ")="
        + n(scale)
        + r"\cdot("
        + n(target)
        + "-("
        + n(h)
        + "))^2+("
        + n(k)
        + ")"
    )
    return html + line(
        name
        + "("
        + n(target)
        + ")="
        + n(scale)
        + r"\cdot("
        + n((target - h) ** 2)
        + ")+("
        + n(k)
        + ")="
        + n(a.result)
    )
