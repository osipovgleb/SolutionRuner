"""Explain strict original domains before discarding numerator candidates."""

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_strict_quotient import source_branches


def domain(a):
    from .exam_trigonometric_proof import formula

    d = a.strict_quotient
    html = "<p>Корень в знаменателе должен быть определён и отличен от нуля. Сохраним также ограничения исходных тригонометрических отношений:</p>"
    html += line(d.radicand_text + ">0")
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(formula(d.radicand) + ">0")
    if sp.denom(d.radicand).free_symbols:
        html += "<p>Умножим неравенство на положительный квадрат ненулевого знаменателя:</p>"
        html += line(formula(a.domain) + ">0")
    if a.domain.free_symbols in ({S}, {C}):
        v = next(iter(a.domain.free_symbols))
        coefficient = a.domain.coeff(v)
        bound = sp.cancel(-a.domain.subs(v, 0) / coefficient)
        html += line(
            formula(v) + (">" if coefficient.is_positive else "<") + sp.latex(bound)
        )
        if v == S and bound == 1 and coefficient.is_negative:
            html += line(r"\sin x\ne1")
        if v == S and bound == 0 and coefficient.is_negative and C in a.poles:
            html += line(r"-1<\sin x<0")
    return html


def rejections(a, candidates):
    from .exam_trigonometric_proof import formula, pi

    html = ""
    for q in sorted({q for b in candidates for q in b.residues} - set(a.residues)):
        values = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        pole = next((p for p in a.poles if sp.simplify(p.subs(values)) == 0), None)
        if pole is not None:
            reason = "Исходное тригонометрическое отношение не определено:"
            check = formula(pole) + "=0"
        else:
            value = sp.simplify(a.strict_quotient.radicand.subs(values))
            reason = (
                "Знаменатель равен нулю:"
                if value == 0
                else "Подкоренное выражение отрицательно:"
            )
            check = a.strict_quotient.radicand_text + "=" + sp.latex(value)
        html += (
            "<p>Эта серия не входит в исходную область определения. " + reason + "</p>"
        )
        html += line("x=" + pi(q) + r"+2\pi k:\quad " + check)
    return html


def tangent(a):
    from .exam_trigonometric_compile import T
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_ratios import ratio_branch
    from .exam_trigonometric_sine_double import linear_double

    c, s = linear_double(a.raw)
    html = line(formula(c) + r"\cos 2x+(" + formula(s) + r")\sin 2x=0")
    html += "<p>Если косинус двойного угла равен нулю, синус равен 1 или −1, и числитель не равен нулю. Поэтому для корней числителя допустимо деление на косинус двойного угла:</p>"
    html += line(r"\cos2x\ne0")
    _, candidates = ratio_branch(a.strict_quotient.polynomial, T)
    html += polynomial(candidates[0], angle="2x", root_scale=sp.Integer(2))
    return html


def numerator(a):
    from .exam_trigonometric_proof import formula, polynomial

    d = a.strict_quotient
    if d.method == "tangent_double":
        return tangent(a)
    html = "<p>На исходной области определения приравняем числитель нулю:</p>"
    html += line(d.numerator_text + "=0")
    for text, value in a.identities:
        if text not in (r"\sin(x)", r"\cos(x)") and not any(
            t in text for t in (r"\tg", r"\ctg")
        ):
            html += line(text + "=" + formula(value))
    if d.method == "grouping":
        other = S if d.variable == C else C
        equivalent = sp.rem(a.raw, S * S + C * C - 1, other)
        weight = sp.cancel(equivalent / (d.variable**2 * d.polynomial))
        html += line(formula(-weight * d.polynomial * (other**2 - 1)) + "=0")
        html += line(formula(weight * d.variable**2 * d.polynomial) + "=0")
        html += line(formula(d.variable**2) + ">0")
        html += "<p>По исходной ОДЗ этот квадрат положителен. Разделим на ненулевой множитель; отдельной ветви нулевого косинуса или синуса здесь нет:</p>"
    for b in source_branches(a, a.allow_inverse):
        html += polynomial(
            b,
            allow_inverse=a.allow_inverse,
            factorization=b.polynomial.subs(b.variable, 0) == 0,
        )
    return html


def proof(a):
    from .exam_trigonometric_proof import families

    d = a.strict_quotient
    prefix = line(a.original)
    html = ""
    if d.method == "tangent_double":
        prefix += line(r"2\cos^{2}x-1=\cos2x")
        html += numerator(a) + domain(a)
    else:
        prefix += domain(a)
        html += numerator(a)
    if d.stage not in ("domain", "double_identity"):
        html = prefix + html
        prefix = "<p>Решим уравнение, сохраняя исходную область определения:</p>"
    html += rejections(a, source_branches(a, a.allow_inverse))
    html += "<p>С учётом всех исходных ограничений получаем серии:</p>"
    html += "".join(line(f + r",\quad k\in\mathbb Z") for f in families(a))
    return prefix, html
