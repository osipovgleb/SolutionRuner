"""A radical denominator requires a strictly positive radicand before clearing it."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, T, U, compile_equation, table
from .power_arithmetic import balanced, clean


def compile_quotient(formula, *, product=False):
    from .exam_trigonometric_methods import Equation

    text = clean(formula).removesuffix(".")
    if not text.startswith(r"\frac{"):
        return None
    numerator, end = balanced(text, 5)
    denominator, end = balanced(text, end)
    if not denominator.startswith(r"\sqrt{"):
        return None
    radicand, root_end = balanced(denominator, 5)
    if "x" not in radicand:
        return None
    if root_end != len(denominator) or text[end:] != "=0":
        raise UnsupportedCondition(
            "one complete quotient by one square root must equal zero"
        )
    try:
        domain, domain_identities = compile_equation(radicand + "=0")
    except UnsupportedCondition:
        return ratio_quotient(numerator, radicand, product)
    if domain.has(T, U):
        return ratio_quotient(numerator, radicand, product)
    if len(domain.free_symbols) != 1 or not domain.free_symbols <= {S, C}:
        raise UnsupportedCondition("the radical denominator needs one sine or cosine")
    variable = next(iter(domain.free_symbols))
    if sp.degree(domain, variable) != 1 or domain.subs(variable, 0) != 0:
        raise UnsupportedCondition("a homogeneous linear radicand is required")
    if product:
        from .exam_trigonometric_angle_product import compile_product

        compiled = compile_product(numerator + "=0")
        return replace(compiled, domain=domain, strict_domain=True)
    raw, identities = compile_equation(numerator + "=0")
    return Equation(
        raw, identities + domain_identities, sp.S.One, domain=domain, strict_domain=True
    )


def ratio_quotient(numerator, radicand, product):
    from .exam_trigonometric_methods import Equation, ExamAngleParser
    from .exam_trigonometric_radical_equation import compile_values

    if product:
        raise UnsupportedCondition(
            "a ratio radicand with separate-angle products is not reviewed"
        )
    atoms, denominators = {}, []
    value = (
        ExamAngleParser(radicand.replace("x", r"\alpha"), atoms, denominators)
        .parse()
        .value
    )
    (ratio,), poles, identities = compile_values([value], atoms, denominators)
    weights = [sp.cancel(ratio * C / S), sp.cancel(ratio * S / C)]
    if not any(
        not w.free_symbols and w.is_real is True and w != 0 for w in weights
    ) or not set(poles) <= {S, C}:
        raise UnsupportedCondition(
            "one homogeneous unit-angle tangent or cotangent radicand is required"
        )
    num, den = sp.fraction(ratio)
    raw, numerator_identities = compile_equation(numerator + "=0")
    return Equation(
        raw,
        numerator_identities + identities,
        sp.S.One,
        poles=poles,
        domain=sp.expand(num * den),
        strict_domain=True,
        radical_ratio=(ratio, radicand),
    )


def proof(a):
    from .exam_trigonometric_proof import formula, pi, polynomial

    html = "<p>Корень в знаменателе должен быть определён и отличен от нуля:</p>"
    if a.radical_ratio:
        ratio, text = a.radical_ratio
        html += line(a.original) + line(text + ">0")
        for pole in a.poles:
            html += line(formula(pole) + r"\ne0")
        for text, value in a.identities:
            if r"\tg" in text or r"\ctg" in text:
                html += line(text + "=" + formula(value))
        html += line(formula(ratio) + ">0")
        html += "<p>При ненулевом знаменателе его квадрат положителен. Умножение на этот квадрат сохраняет строгое неравенство:</p>"
    html += line(formula(a.domain) + ">0")
    html += "<p>Только при этом условии исходное уравнение равносильно обращению числителя в нуль:</p>"
    if a.angle_product is not None:
        return (
            "<p>Решим уравнение с сохранением области определения знаменателя:</p>",
            html + product_proof(a),
        )
    for text, value in a.identities:
        if a.radical_ratio and (r"\tg" in text or r"\ctg" in text):
            continue
        html += line(text + "=" + formula(value))
    html += line(formula(a.raw) + "=0")
    html += line(formula(a.reduced) + "=0")
    for branch in a.branches:
        html += polynomial(
            branch, allowed_residues=branch.residues, factorization=a.factorization
        )
        for value in branch.values:
            for q in table(branch.variable, value):
                if q in branch.residues:
                    continue
                radicand = sp.simplify(
                    (a.radical_ratio[0] if a.radical_ratio else a.domain).subs(
                        {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
                    )
                )
                html += (
                    "<p>Эта серия не удовлетворяет строгому условию на знаменатель:</p>"
                )
                html += line(
                    "x=" + pi(q) + r"+2\pi k:\quad" + sp.latex(radicand) + r"\le0"
                )
    if a.radical_ratio:
        from .exam_trigonometric_proof import families

        html += "<p>Сдвиг начального значения на целое число периодов лишь меняет целый параметр. Запишем оставшуюся серию в равносильной форме:</p>"
        for text in families(a):
            html += line(text + r",\quad k\in\mathbb Z")
    return "<p>Решим уравнение с сохранением области определения знаменателя:</p>", html


def product_proof(a):
    from .exam_trigonometric_angle_product import branches
    from .exam_trigonometric_angle_product import proof as angle_proof
    from .exam_trigonometric_proof import families, pi

    unfiltered = branches(a.angle_product)
    html = angle_proof(replace(a, branches=unfiltered))[1]
    rejected = sorted({q for b in unfiltered for q in b.residues} - set(a.residues))
    for q in rejected:
        value = sp.simplify(a.domain.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}))
        if value.is_nonpositive is not True:
            raise UnsupportedCondition("only nonpositive radicands may be excluded")
        html += "<p>Эта серия не удовлетворяет строгому условию на знаменатель:</p>"
        html += line("x=" + pi(q) + r"+2\pi k:\quad" + sp.latex(value) + r"\le0")
    html += "<p>После отбора по области определения остаются серии:</p>"
    for text in families(a):
        html += line(text + r",\quad k\in\mathbb Z")
    return html
