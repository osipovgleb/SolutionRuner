"""A radical denominator requires a strictly positive radicand before clearing it."""

import sympy as sp

from ..probability.common import line
from ..word_problems.common import UnsupportedCondition
from .exam_trigonometric_compile import C, S, compile_equation, table
from .power_arithmetic import balanced, clean


def compile_quotient(formula):
    from .exam_trigonometric_methods import Equation

    text = clean(formula)
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
    raw, identities = compile_equation(numerator + "=0")
    domain, domain_identities = compile_equation(radicand + "=0")
    if len(domain.free_symbols) != 1 or not domain.free_symbols <= {S, C}:
        raise UnsupportedCondition("the radical denominator needs one sine or cosine")
    variable = next(iter(domain.free_symbols))
    if sp.degree(domain, variable) != 1 or domain.subs(variable, 0) != 0:
        raise UnsupportedCondition("a homogeneous linear radicand is required")
    return Equation(
        raw, identities + domain_identities, sp.S.One, domain=domain, strict_domain=True
    )


def proof(a):
    from .exam_trigonometric_proof import formula, pi, polynomial

    html = "<p>Корень в знаменателе должен быть определён и отличен от нуля:</p>"
    html += line(formula(a.domain) + ">0")
    html += "<p>Только при этом условии исходное уравнение равносильно обращению числителя в нуль:</p>"
    for text, value in a.identities:
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
                    a.domain.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)})
                )
                html += (
                    "<p>Эта серия не удовлетворяет строгому условию на знаменатель:</p>"
                )
                html += line(
                    "x=" + pi(q) + r"+2\pi k:\quad" + sp.latex(radicand) + r"\le0"
                )
    return "<p>Решим уравнение с сохранением области определения знаменателя:</p>", html
