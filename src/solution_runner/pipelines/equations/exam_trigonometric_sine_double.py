"""Project onto a double-angle sine using an exact unit-circle remainder."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


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


def prepare(equation, preferred, scale):
    if (
        preferred != S
        or scale != 2 * equation.scale
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
        return equation
    polynomial = project(equation.raw)
    if polynomial is None:
        return equation
    return replace(
        equation,
        raw=polynomial,
        scale=scale,
        identities=(),
        sine_double=(equation.raw, equation.scale),
    )


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    raw, base = a.sine_double
    source, angle = argument(base), argument(a.scale)
    html = line(a.original)
    html += "<p>Применим основное тригонометрическое тождество и формулу синуса двойного угла:</p>"
    html += line(formula(S * S + C * C, source) + "=1")
    html += line(formula(S, angle) + "=" + formula(2 * S * C, source))
    html += line(formula(raw, source) + "=0")
    html += line(formula(a.raw, angle) + "=0")
    for b in a.branches:
        html += polynomial(b, angle=angle, root_scale=a.scale)
    return "<p>Сведём уравнение к синусу двойного угла:</p>", html
