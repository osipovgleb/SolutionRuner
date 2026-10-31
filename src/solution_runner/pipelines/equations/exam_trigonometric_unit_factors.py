"""Split a cubic factor on the unit circle into three affine branches."""

from dataclasses import replace

import sympy as sp

from ..probability.common import line
from .exam_trigonometric_compile import C, S


def prepare(equation):
    raw = equation.raw
    if (
        equation.poles
        or not raw.is_polynomial(S, C)
        or sp.Poly(raw, S, C).total_degree() != 3
    ):
        return None
    _coefficient, factors = sp.factor_list(raw, S, C, extension=True)
    if len(factors) != 2 or any(power != 1 for _, power in factors):
        return None
    linear = next(
        (
            f
            for f, _ in factors
            if sp.Poly(f, S, C).total_degree() == 1
            and f.free_symbols == {S, C}
            and f.subs({S: 0, C: 0}) == 0
        ),
        None,
    )
    if linear is None:
        return None
    quotient = sp.cancel(raw / linear)
    reduced = sp.rem(quotient, S * S + C * C - 1, S)
    pairs = sp.factor_list(reduced, S, C, extension=True)[1]
    if len(pairs) != 2 or any(
        power != 1
        or f.free_symbols not in ({S}, {C})
        or sp.degree(f, next(iter(f.free_symbols))) != 1
        for f, power in pairs
    ):
        return None
    product = sp.factor(reduced, extension=True) * linear
    if sp.rem(sp.expand(raw - product), S * S + C * C - 1, S) != 0:
        return None
    return replace(
        equation, raw=sp.expand(product), unit_factors=(raw, linear, quotient, reduced)
    )


def branches(equation, allow_inverse):
    from .exam_trigonometric import solve_branches

    result = solve_branches(equation.raw, C, allow_inverse, factored=True)[1]
    return tuple(sorted(result, key=lambda b: b.original is None))


def proof(a):
    from .exam_trigonometric_proof import formula, polynomial
    from .exam_trigonometric_variants import argument

    raw, linear, quotient, reduced = a.unit_factors
    angle = argument(a.scale)
    html = line(a.original)
    html += line(formula(raw, angle) + "=0")
    html += "<p>Применим формулы суммы кубов и разности квадратов, вынесем общий множитель:</p>"
    html += line(formula(sp.Mul(linear, quotient, evaluate=False), angle) + "=0")
    html += line(formula(S * S + C * C, angle) + "=1")
    html += line(formula(sp.Mul(linear, reduced, evaluate=False), angle) + "=0")
    html += "<p>Разложим оставшуюся скобку и решим все три уравнения:</p>"
    html += line(
        formula(
            sp.Mul(linear, sp.factor(reduced, extension=True), evaluate=False), angle
        )
        + "=0"
    )
    for branch in a.branches:
        html += polynomial(branch, angle=angle, root_scale=a.scale)
    return (
        "<p>Разложим выражение на множители с помощью основного тригонометрического тождества:</p>",
        html,
    )
