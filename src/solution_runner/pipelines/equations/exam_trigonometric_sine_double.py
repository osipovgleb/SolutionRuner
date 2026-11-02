"""Project onto a double-angle sine using an exact unit-circle remainder."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def shifted_square_parent(html):
    compact = "".join(html.split())
    if not all(token in compact for token in (r"\sin2x=", r"\sin^{2}", r"\cos^{2}")):
        return None
    from bs4 import BeautifulSoup

    from ..word_problems.common import UnsupportedCondition
    from .exam_trigonometric_methods import parse_equation
    from .power_arithmetic import clean

    forms = [
        "".join(n["data-inline-latex"].split())
        for n in BeautifulSoup(html, "html.parser").select("[data-inline-latex]")
    ]
    if not forms or not any(r"\sin2x=" in f for f in forms):
        return None
    if not any(r"\sin^{2}" in f and r"\cos^{2}" in f for f in forms):
        return None
    parts = clean(forms[0]).rstrip(".").split("=")
    if len(parts) < 2:
        return None
    try:
        values, atoms, denominators = parse_equation(parts[0] + "=" + parts[-1])
    except UnsupportedCondition:
        return None
    if len(atoms) != 2 or denominators:
        return None
    (left, sine), (right, cosine) = atoms.items()
    if (
        values != [left, right]
        or (sine.function, cosine.function) != ("sin", "cos")
        or sine.coefficient != 1
        or cosine.coefficient != 1
        or sine.shift - cosine.shift != sp.Rational(1, 2)
    ):
        return None
    return sine.shift, cosine.shift


def shifted_square(formula):
    from ..word_problems.common import UnsupportedCondition
    from .exam_trigonometric_methods import constant_angles, parse_equation

    values, atoms, denominators = parse_equation(formula)
    values, atoms, denominators, _ = constant_angles(values, atoms, denominators)
    if len(atoms) != 2 or any(d.free_symbols or d == 0 for d in denominators):
        raise UnsupportedCondition(
            "one shifted square and one double-angle cosine are required"
        )
    sine = [
        (s, a) for s, a in atoms.items() if a.function == "sin" and a.coefficient == 1
    ]
    cosine = [
        (s, a)
        for s, a in atoms.items()
        if a.function == "cos" and a.coefficient == 2 and a.shift == 0
    ]
    if len(sine) != 1 or len(cosine) != 1:
        raise UnsupportedCondition(
            "the shifted-square method requires its original unit and double angles"
        )
    (s, atom), (c, _) = sine[0], cosine[0]
    left, target = values
    weight, double = left.coeff(s, 2), left.coeff(c)
    phase = atom.shift - sp.Rational(1, 2)
    if (
        sp.expand(left - weight * s**2 - double * c) != 0
        or not weight
        or not double
        or any(
            v.free_symbols or v.is_real is not True or abs(v) > 1000
            for v in (weight, double, target)
        )
        or not (12 * phase).is_Integer
        or abs(phase) > 2
    ):
        raise UnsupportedCondition(
            "bounded closed coefficients and a reviewed twelfth-turn shift are required"
        )
    sine_coefficient = sp.simplify(-weight * sp.sin(2 * phase * sp.pi) / 2)
    if (
        sp.simplify(weight * sp.cos(2 * phase * sp.pi) / 2 + double) != 0
        or sine_coefficient == 0
    ):
        raise UnsupportedCondition(
            "the double-angle cosine must cancel exactly, leaving a nonzero sine"
        )
    return weight, double, target, atom.shift


def linear_double(raw):
    from ..word_problems.common import UnsupportedCondition

    constant = raw.subs({S: 0, C: 0})
    homogeneous = sp.expand(raw + constant * (S * S + C * C - 1))
    a, b = homogeneous.coeff(C, 2), homogeneous.coeff(S).coeff(C) / 2
    if (
        sp.expand(homogeneous - a * (C * C - S * S) - 2 * b * S * C) != 0
        or a == 0
        or b == 0
    ):
        raise UnsupportedCondition(
            "a nondegenerate linear double-angle sine/cosine equation is required"
        )
    return a, b


def project(raw):
    if (
        raw.free_symbols - {S, C}
        or not raw.is_polynomial(S, C)
        or sp.Poly(raw, S, C).total_degree() > 4
    ):
        return None
    a, b, c = sp.symbols("A B D")
    remainder = sp.rem(
        raw - (a * (2 * S * C) ** 2 + b * 2 * S * C + c), S * S + C * C - 1, S
    )
    solutions = sp.solve(sp.Poly(remainder, S, C).coeffs(), (a, b, c), dict=True)
    if len(solutions) != 1 or set(solutions[0]) != {a, b, c}:
        return None
    result = sp.expand((a * S * S + b * S + c).subs(solutions[0]))
    return result if result != 0 and sp.degree(result, S) in (1, 2) else None


def prepare(equation, preferred, scale, *, formula="", parent_html=""):
    from ..word_problems.common import UnsupportedCondition

    reviewed = bool(formula and shifted_square_parent(parent_html) is not None)
    certificate = shifted_square(formula) if reviewed else None
    preprojected = (
        certificate is not None and preferred == S and scale == equation.scale
    )
    if (
        preferred != S
        or (scale != 2 * equation.scale and not preprojected)
        or equation.poles
        or equation.domain is not None
        or equation.angle_product is not None
        or (
            equation.log_product is not None
            and equation.log_product.equality is not None
            and (
                equation.log_product.equality.linear is not None
                or equation.log_product.equality.variable is not None
                or equation.log_product.equality.identity is not None
            )
        )
    ):
        if reviewed:
            raise UnsupportedCondition(
                "the shifted square requires its original denominator-free unit angle"
            )
        return equation
    specialized = (
        equation.sum_product,
        equation.triple_angle,
        equation.ratio_product,
        equation.square_difference,
        equation.square_product,
        equation.symmetric,
        equation.reciprocal,
        equation.affine,
        equation.absolute,
        equation.positive_factorization,
        equation.absolute_fraction,
        equation.cosine_equality,
        equation.argument_pair,
        equation.sum_squares,
        equation.radical_equation,
        equation.radical_ratio,
        equation.bounded_log,
        equation.global_radical,
        equation.square_radicals,
    )
    if any(value is not None for value in specialized):
        if reviewed:
            raise UnsupportedCondition(
                "the shifted-square certificate cannot replace another parent method"
            )
        return equation
    polynomial = equation.raw if preprojected else project(equation.raw)
    if polynomial is None:
        if reviewed:
            raise UnsupportedCondition(
                "the shifted square must project onto the double-angle sine"
            )
        return equation
    source = projection_source(equation, polynomial, certificate, preprojected)
    return replace(
        equation,
        raw=polynomial,
        scale=scale,
        identities=(),
        sine_double=source + ((certificate,) if certificate is not None else ()),
    )


def projection_source(equation, polynomial, certificate, preprojected):
    from ..word_problems.common import UnsupportedCondition

    if certificate is not None:
        weight, _double, target, beta = certificate
        expected = (
            -weight * sp.sin(2 * (beta - sp.Rational(1, 2)) * sp.pi) * S / 2
            + weight / 2
            - target
        )
        if sp.simplify(polynomial - expected) != 0:
            raise UnsupportedCondition(
                "the source square and projected equation must agree exactly"
            )
    source_raw, source_scale = equation.raw, equation.scale
    if preprojected:
        weight, double, target, beta = certificate
        source_raw = sp.expand(
            weight * (S * sp.cos(beta * sp.pi) + C * sp.sin(beta * sp.pi)) ** 2
            + double * (C * C - S * S)
            - target
        )
        source_scale = sp.Rational(source_scale, 2)
    return source_raw, source_scale


def shifted_square_steps(a, certificate):
    weight, double, target, beta = certificate
    x = sp.Symbol("x", real=True)
    phase = (beta - sp.Rational(1, 2)) * sp.pi
    shifted = sp.cos(x + phase, evaluate=False)
    higher = sp.cos(2 * x + 2 * phase, evaluate=False)
    cosine, sine = sp.cos(2 * x), sp.sin(2 * x)
    expanded = cosine * sp.cos(2 * phase) - sine * sp.sin(2 * phase)
    html = "<p>Применим формулу приведения к сдвинутому синусу:</p>"
    html += line(
        sp.latex(sp.sin(x + beta * sp.pi, evaluate=False))
        + "="
        + sp.latex(sp.sin(sp.Add(x, sp.pi / 2, phase, evaluate=False), evaluate=False))
        + "="
        + sp.latex(shifted)
    )
    html += line(
        sp.latex(weight * shifted**2 + double * cosine) + "=" + sp.latex(target)
    )
    html += "<p>Понизим степень косинуса по формуле двойного угла:</p>"
    html += line(sp.latex(shifted**2) + "=" + sp.latex((1 + higher) / 2))
    html += line(
        sp.latex(weight * (1 + higher) / 2 + double * cosine) + "=" + sp.latex(target)
    )
    html += "<p>Раскроем косинус суммы и сократим противоположные слагаемые:</p>"
    html += line(sp.latex(higher) + "=" + sp.latex(expanded))
    uncancelled = sp.Add(
        sp.Mul(weight / 2, expanded, evaluate=False),
        weight / 2,
        double * cosine,
        evaluate=False,
    )
    html += line(sp.latex(uncancelled) + "=" + sp.latex(target))
    html += line(sp.latex(sp.expand(uncancelled)) + "=" + sp.latex(target))
    from .exam_trigonometric_proof import formula

    html += line(formula(a.raw, "2x") + "=0")
    return html


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    raw, base = a.sine_double[:2]
    source, angle = argument(base), argument(a.scale)
    html = line(a.original)
    if len(a.sine_double) == 3:
        html += shifted_square_steps(a, a.sine_double[2])
    else:
        html += "<p>Применим основное тригонометрическое тождество и формулу синуса двойного угла:</p>"
        html += line(formula(S * S + C * C, source) + "=1")
        html += line(formula(S, angle) + "=" + formula(2 * S * C, source))
        html += line(formula(raw, source) + "=0")
        html += line(formula(a.raw, angle) + "=0")
    for b in a.branches:
        html += polynomial(b, angle=angle, root_scale=a.scale)
    return "<p>Сведём уравнение к синусу двойного угла:</p>", html
