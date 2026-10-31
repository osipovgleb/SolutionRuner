"""Retain the substitution by the difference of sine and cosine."""

import sympy as sp

from ..probability.common import line
from .exam_exponential import X
from .exam_logarithmic_algebra import roots
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_symmetric import V


def proof(a):
    from .exam_trigonometric_proof import families, formula

    data = a.symmetric
    t = sp.Symbol(data.variable, real=True)
    html = line(a.original)
    html += "<p>Применим формулу синуса разности и обозначим разность синуса и косинуса:</p>"
    html += line(data.variable + "=" + formula(S - C))
    html += line(formula((S - C) ** 2) + "=1-" + formula(2 * S * C))
    html += line(r"\sin 2x=1-" + sp.latex(t * t))
    p = data.polynomial.subs(V, t)
    html += line(sp.latex(p) + "=0") + line(
        sp.latex(sp.factor(p, extension=True)) + "=0"
    )
    for factor, _ in sp.factor_list(p, t, extension=True)[1]:
        if sp.degree(factor, t) == 2:
            aa, bb, cc = sp.Poly(factor, t).all_coeffs()
            d = sp.simplify(bb * bb - 4 * aa * cc)
            html += line("D=" + sp.latex(d))
            if d.is_negative:
                html += "<p>Квадратный множитель действительных нулей не имеет.</p>"
    for value in roots(data.polynomial.subs(V, X)):
        html += line(data.variable + "=" + sp.latex(value))
    html += "<p>Вернёмся к исходной переменной:</p>"
    for b in a.branches:
        if b.impossible:
            html += "<p>Это значение выходит за область значений разности синуса и косинуса.</p>"
            continue
        value = sp.simplify(-b.original.subs({S: 0, C: 0}))
        html += line(formula(S - C) + "=" + sp.latex(value))
        html += line(r"\sqrt{2}\sin\left(x-\frac{\pi}{4}\right)=" + sp.latex(value))
        html += line(
            r"\sin\left(x-\frac{\pi}{4}\right)=" + sp.latex(value / sp.sqrt(2))
        )
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Выполним замену разности синуса и косинуса:</p>", html
