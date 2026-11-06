"""Certify and order rational and quadratic-radical boundaries without floats."""

from functools import cmp_to_key

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_scalar import compare, enclose
from .rational_inequality_parser import X, polynomial


def ordered(values):
    exact = []
    for value in values:
        value = sp.simplify(sp.radsimp(value))
        enclose(value, 32)
        exact.append(value)
    result = []
    for value in sorted(exact, key=cmp_to_key(compare)):
        if not result or compare(value, result[-1]) != 0:
            result.append(value)
    return tuple(result)


def quadratic_roots(p):
    if p.degree() == 1:
        return [-p.nth(0) / p.nth(1)]
    if p.degree() != 2:
        raise UnsupportedCondition("the algebraic factor must be linear or quadratic")
    a, b, c = p.all_coeffs()
    discriminant = sp.simplify(b * b - 4 * a * c)
    if discriminant.has(sp.log):
        discriminant = sp.expand_log(discriminant)
    sign = compare(discriminant, 0)
    if sign < 0:
        return []
    radical = sp.sqrtdenest(sp.sqrt(discriminant))
    return [
        sp.simplify((-b - radical) / (2 * a)),
        sp.simplify((-b + radical) / (2 * a)),
    ]


def real_roots(value):
    p = polynomial(value)
    if p.is_zero:
        raise UnsupportedCondition("the original denominator is identically zero")
    if all(c.is_Rational is True for c in p.all_coeffs()):
        return ordered(sp.real_roots(p))
    _, factors = sp.factor_list(p.as_expr(), X, extension=True)
    return ordered(
        root for factor, _ in factors for root in quadratic_roots(sp.Poly(factor, X))
    )
