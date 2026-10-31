"""Explain the union of affine roots and periodic trigonometric solutions."""

import sympy as sp

from ..probability.common import line
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    html = line(formula(a.affine.source) + "=0")
    quotient = sp.cancel(a.affine.source / a.affine.algebraic)
    terms = []
    for powers, coefficient in sp.Poly(quotient, S, C).terms():
        term = coefficient * S ** powers[0] * C ** powers[1]
        terms.append(
            a.affine.algebraic
            if term == 1
            else sp.Mul(term, a.affine.algebraic, evaluate=False)
        )
    html += line(formula(sp.Add(*terms, evaluate=False)) + "=0")
    html += line(formula(sp.factor(a.affine.source)) + "=0")
    html += "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю. Сначала решим тригонометрическое уравнение:</p>"
    for branch in a.branches:
        html += polynomial(branch)
    html += "<p>Алгебраический множитель даёт отдельные корни, которые не образуют периодическую серию:</p>"
    html += line(sp.latex(a.affine.algebraic) + "=0")
    for root in a.affine.roots:
        html += line("x=" + sp.latex(root))
    return "<p>Сгруппируем слагаемые и вынесем общий множитель:</p>", html


def selection(a):
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric_proof import pi

    lo, hi, lc, uc = a.bounds
    html = (
        "<p>На числовой прямой отберём корни, принадлежащие промежутку "
        + inline(a.interval)
        + ":</p>"
    )
    for root in a.selected:
        html += line(
            pi(lo)
            + (r"\le" if lc else "<")
            + pi(root)
            + (r"\le" if uc else "<")
            + pi(hi)
        )
    if not a.selected:
        html += "<p>На указанном промежутке корней нет.</p>"
    for root in a.affine.roots:
        if compare(root, lo * sp.pi) < 0:
            html += line(sp.latex(root) + "<" + pi(lo))
        elif compare(root, hi * sp.pi) > 0:
            html += line(sp.latex(root) + ">" + pi(hi))
    return html
