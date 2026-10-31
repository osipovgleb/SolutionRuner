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
    domain, domain_identities = compile_equation(inner + "=0")
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
    from .exam_trigonometric_methods import Equation, compile_reviewed

    try:
        factor, identities = compile_equation(prefix + "=0")
    except UnsupportedCondition:
        if not any(token in prefix for token in (r"\tg", r"\ctg")):
            raise
        equation = compile_reviewed(prefix + "=0", C, sp.S.One)
        if (
            equation.scale != 1
            or not equation.poles
            or any(p.free_symbols != {variable} for p in equation.poles)
        ):
            raise UnsupportedCondition(
                "the radical ratio must share one original nonzero function"
            )
        raw = (
            equation.factored_source
            if equation.factored_source is not None
            else equation.raw
        )
        return replace(
            equation,
            raw=raw,
            domain=domain,
            factored_source=None,
            cleared_denominator=None,
        )
    if factor.free_symbols - {S, C}:
        raise UnsupportedCondition(
            "the polynomial factor must use only sine and cosine"
        )
    return Equation(
        sp.expand(factor * domain),
        identities + domain_identities,
        sp.S.One,
        domain=domain,
    )


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


def ratio_proof(a):
    from ..probability.common import line
    from .exam_trigonometric_proof import formula, polynomial

    html = "<p>Корень должен быть определён, а знаменатель тригонометрического отношения — отличен от нуля:</p>"
    html += line(formula(a.domain) + r"\ge0")
    for pole in a.poles:
        html += line(formula(pole) + r"\ne0")
    html += line(formula(a.domain) + ">0")
    html += "<p>Поэтому корень положителен. Разделим на него только на исходной области определения и разложим оставшееся произведение:</p>"
    html += line(a.original)
    html += line(formula(sp.factor(a.raw, extension=True)) + "=0")
    for branch in a.branches:
        html += polynomial(branch, allowed_residues=branch.residues)
    html += (
        "<p>Из каждой серии оставлены только точки исходной области определения.</p>"
    )
    return "<p>Сохраним область определения до деления на радикал:</p>", html


def without_poles(branches, poles):
    from .exam_trigonometric_compile import C, S
    from .exam_trigonometric_inverse import angles

    if not poles:
        return branches
    result = []
    for branch in branches:
        multiplier = sp.sympify(branch.angle_scale)
        if multiplier.is_Integer is not True or not 1 <= multiplier <= 12:
            raise UnsupportedCondition(
                "pole filtering requires a bounded positive integer branch angle"
            )
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
                (((q - branch.angle_shift) % 2 if branch.angle_shift else q) + 2 * k)
                / branch.angle_scale
                in residues
                for q in angles(branch.variable, v, True)
                for k in range(int(branch.angle_scale))
            )
        )
        excluded = tuple(v for v in branch.values if v not in values)
        result.append(
            replace(branch, residues=residues, values=values, excluded=excluded)
        )
    return tuple(result)


def validate_circle_domain(entry, a):
    from .exam_trigonometric_compile import C, S
    from .exam_trigonometric_inverse import decode

    multiplier = sp.Rational(entry.get("circle_scale", "1"))
    if multiplier <= 0:
        raise UnsupportedCondition(
            "a circle domain certificate requires a positive angle multiplier"
        )
    for point in entry.get("excluded_markers", []):
        q = a.scale * (decode(point["angle"]) / multiplier + a.translation)
        substitution = {S: sp.sin(q * sp.pi), C: sp.cos(q * sp.pi)}
        pole = any(sp.simplify(p.subs(substitution)) == 0 for p in a.poles)
        negative = a.domain is not None and compare(
            sp.simplify(a.domain.subs(substitution)), sp.S.Zero
        ) < (1 if a.strict_domain else 0)
        if not (pole or negative):
            raise UnsupportedCondition(
                "every crossed circle point must violate the original domain"
            )
    shading = entry.get("domain_shading")
    if shading:
        variable = {"sin": S, "cos": C}.get(shading.get("variable"))
        if (
            variable is None
            or a.domain != variable
            or variable not in a.poles
            or shading.get("side") != "nonpositive"
        ):
            raise UnsupportedCondition(
                "the shaded half-circle must match the complete original domain"
            )
