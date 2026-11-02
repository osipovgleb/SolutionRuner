"""Explain the union of affine roots and periodic trigonometric solutions."""

import sympy as sp

from ..probability.common import line
from .exam_scalar import compare
from .exam_trigonometric_compile import C, S


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    if a.affine.quadratic:
        return quadratic_proof(a)
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


def quadratic_proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    data = a.affine
    html = line(a.original) + line(formula(sp.factor(data.source)) + "=0")
    scalar = sp.cancel(data.source / (data.algebraic * a.raw))
    if scalar != 1:
        html += line(sp.latex(scalar) + r"\ne0")
        html += "<p>Ненулевой числовой множитель не влияет на равенство произведения нулю.</p>"
    algebraic = "<p>Решим алгебраическое уравнение:</p>"
    algebraic += line(sp.latex(data.algebraic) + "=0")
    algebraic += line(sp.latex(sp.factor(data.algebraic)) + "=0")
    for root in data.roots:
        algebraic += line("x=" + sp.latex(root))
    algebraic += (
        "<p>Это отдельные корни в радианах; они не образуют периодическую серию.</p>"
    )
    trig = "<p>Решим тригонометрическое уравнение:</p>"
    for branch in a.branches:
        trig += polynomial(branch)
    html += algebraic + trig if data.algebraic_first else trig + algebraic
    return (
        "<p>Произведение равно нулю, когда хотя бы один множитель равен нулю:</p>",
        html,
    )


def isolated_selection(a):
    from ..word_problems.water_season_proof import inline
    from .exam_trigonometric_affine_selection import isolated
    from .exam_trigonometric_proof import pi

    lo, hi, lc, uc = a.bounds
    selected = isolated(a.affine.roots, a.bounds)
    html = (
        "<p>Отдельные алгебраические корни сравним с границами промежутка "
        + inline(a.interval)
        + ":</p>"
    )
    for root in a.affine.roots:
        if sp.cancel(root / sp.pi) in selected:
            html += line(
                pi(lo)
                + (r"\le" if lc else "<")
                + sp.latex(root)
                + (r"\le" if uc else "<")
                + pi(hi)
            )
        elif compare(root, lo * sp.pi) < 0:
            html += line(sp.latex(root) + "<" + pi(lo))
        elif compare(root, hi * sp.pi) > 0:
            html += line(sp.latex(root) + ">" + pi(hi))
        else:
            endpoint = lo if compare(root, lo * sp.pi) == 0 else hi
            html += line(sp.latex(root) + "=" + pi(endpoint))
            html += (
                "<p>Эта граница промежутка не включена, поэтому корень не подходит.</p>"
            )
    return html
