"""Retain guarded tangent division and the parent's cubic grouping."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S, T, U
from .exam_trigonometric_variants import argument


def grouped(branch, substitution, angle, scale):
    from .exam_trigonometric_proof import candidate_lines, formula

    variable = sp.Symbol(substitution, real=True) if substitution else T
    p = branch.polynomial
    root = next(v for v in branch.candidates if v.is_Integer and v < 0)
    quotient = sp.div(p, T - root, T)[0]
    terms = [
        coefficient * T ** power[0] * (T - root)
        for power, coefficient in sp.Poly(quotient, T).terms()
    ]
    html = "<p>Сгруппируем слагаемые и вынесем общий множитель:</p>"
    html += line(
        "+".join("(" + formula(term.subs(T, variable), angle) + ")" for term in terms)
        + "=0"
    )
    html += line(formula(((T - root) * quotient).subs(T, variable), angle) + "=0")
    a, b, c = sp.Poly(quotient, T).all_coeffs()
    html += line("D=" + sp.latex(b * b - 4 * a * c))
    return html + candidate_lines(branch, substitution, angle=angle, root_scale=scale)


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial

    reduction = a.homogeneous
    source_angle, angle = argument(reduction.source_scale), argument(a.scale)
    intro = "<p>Используем тригонометрические тождества и приведём уравнение к однородному:</p>"
    html = ""
    if a.power_angle is not None:
        from .exam_trigonometric_power_identity import proof as power_proof

        html += power_proof(a.power_angle)
    if a.poles:
        html += "<p>Знаменатель исходного уравнения должен быть ненулевым:</p>"
        for pole in a.poles:
            html += line(formula(pole, source_angle) + r"\ne0")
    if a.rewritten is not None:
        html += line(sp.latex(a.rewritten) + "=0")
    for text, value in a.identities:
        html += line(text + "=" + formula(value, source_angle))
    html += line(formula(reduction.source, source_angle) + "=0")
    html += line(formula(S * S + C * C, source_angle) + "=1")
    if a.scale != reduction.source_scale:
        html += "<p>Применим формулы двойного угла:</p>"
        html += line(formula(S, angle) + "=" + formula(2 * S * C, source_angle))
        html += line(formula(C, angle) + "=" + formula(C * C - S * S, source_angle))
    html += line(formula(reduction.polynomial, angle) + "=0")
    if reduction.variable == U:
        html += "<p>Если синус равен нулю, косинус равен 1 или −1, и однородный многочлен ненулевой. Поэтому на множестве решений синус ненулевой; разделим уравнение на его степень:</p>"
    else:
        html += "<p>Если косинус равен нулю, синус равен 1 или −1. Тогда однородный многочлен равен ненулевому коэффициенту при старшей степени синуса, умноженному на эту степень, поэтому решений нет. Следовательно, косинус ненулевой; разделим уравнение на его степень:</p>"
    denominator = S if reduction.variable == U else C
    html += line(formula(denominator**reduction.degree, angle) + r"\ne0")
    if a.substitution:
        html += line(a.substitution + "=" + formula(reduction.variable, angle))
    branch = a.branches[0]
    if reduction.degree == 3 and any(v.is_Integer and v < 0 for v in branch.candidates):
        html += grouped(branch, a.substitution, angle, a.scale)
    else:
        html += polynomial(
            branch,
            a.substitution,
            factorization=a.factorization,
            angle=angle,
            root_scale=a.scale,
        )
    return intro, html
