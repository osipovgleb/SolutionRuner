"""Keep the domain and both zero factors of a reviewed radical product."""

from dataclasses import replace

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_scalar import compare
from .power_arithmetic import balanced, clean


def radical_product(formula):
    from .exam_trigonometric import C, S, compile_equation

    text = clean(formula)
    candidates = []
    start = 0
    while (index := text.find(r"\sqrt{", start)) >= 0:
        inner, end = balanced(text, index + 5)
        if "x" in inner:
            candidates.append((index, inner, end))
        start = end
    if not candidates:
        return None
    if len(candidates) != 1:
        raise UnsupportedCondition("one variable radical factor is required")
    index, inner, end = candidates[0]
    prefix = text[:index]
    if text[end:] != "=0" or not prefix.startswith("(") or not prefix.endswith(")"):
        raise UnsupportedCondition(
            "a complete parenthesized factor times a square root must equal zero"
        )
    factor, identities = compile_equation(prefix + "=0")
    domain, domain_identities = compile_equation(inner + "=0")
    if factor.free_symbols - {S, C}:
        raise UnsupportedCondition(
            "the polynomial factor must use only sine and cosine"
        )
    variables = domain.free_symbols & {S, C}
    if len(variables) != 1:
        raise UnsupportedCondition(
            "the radicand must be a scalar times one sine or cosine"
        )
    variable = next(iter(variables))
    if sp.degree(domain, variable) != 1 or domain.subs(variable, 0) != 0:
        raise UnsupportedCondition(
            "a homogeneous linear trigonometric radicand is required"
        )
    return sp.expand(factor * domain), identities + domain_identities, domain


def restrict(branches, domain, strict=False):
    from .exam_trigonometric import C, S

    result = []
    for branch in branches:
        residues = tuple(
            q
            for q in branch.residues
            if compare(
                sp.simplify(domain.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)})),
                sp.Integer(0),
            )
            >= (1 if strict else 0)
        )
        result.append(replace(branch, residues=residues))
    return tuple(result)


def proof(a):
    from ..probability.common import line
    from .exam_trigonometric import C, S, table
    from .exam_trigonometric_proof import formula, pi, polynomial

    variable = next(iter(a.domain.free_symbols))
    coefficient = a.domain.coeff(variable)
    html = "<p>Квадратный корень определён при условии:</p>"
    html += line(
        formula(a.domain)
        + r"\ge0\quad\Longleftrightarrow\quad"
        + formula(variable)
        + (r"\ge0" if compare(coefficient, sp.Integer(0)) > 0 else r"\le0")
    )
    html += "<p>В этой области произведение равно нулю, когда равен нулю хотя бы один множитель. Ветвь с нулевым подкоренным выражением также сохраняем:</p>"
    for branch in a.branches:
        html += polynomial(branch, allowed_residues=branch.residues)
        for value in branch.values:
            for q in table(branch.variable, value):
                if q not in branch.residues:
                    radicand = sp.simplify(
                        a.domain.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)})
                    )
                    html += "<p>Эта серия не входит в область определения:</p>"
                    html += line(
                        "x=" + pi(q) + r"+2\pi k:\quad" + sp.latex(radicand) + "<0"
                    )
    html += "<p>В каждой серии оставлены только точки, удовлетворяющие области определения квадратного корня.</p>"
    return (
        "<p>Решим уравнение, учитывая область определения квадратного корня:</p>",
        html,
    )


def without_poles(branches, poles):
    from .exam_trigonometric_compile import C, S
    from .exam_trigonometric_inverse import angles

    if not poles:
        return branches
    result = []
    for branch in branches:
        residues = tuple(
            q
            for q in branch.residues
            if all(
                sp.simplify(p.subs({S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)})) != 0
                for p in poles
            )
        )
        values = tuple(
            v
            for v in branch.values
            if any(
                ((q - branch.angle_shift) % 2 if branch.angle_shift else q) in residues
                for q in angles(branch.variable, v, True)
            )
        )
        excluded = tuple(v for v in branch.values if v not in values)
        result.append(
            replace(branch, residues=residues, values=values, excluded=excluded)
        )
    return tuple(result)
