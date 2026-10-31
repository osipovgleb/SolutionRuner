"""Normalize commensurate powers by an exact positive factor, without solving x."""

from functools import reduce
from math import gcd, lcm

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_exponential import T, X


def normalize(powers, constant):
    bases = {p[1] for p in powers}
    primes = set().union(*(set(sp.factorint(b)) for b in bases))
    if len(bases) == 1:
        basis = next(iter(bases))
    elif len(primes) == 1:
        basis = sp.Integer(next(iter(primes)))
    else:
        if len(powers) != 3 or constant != 0:
            raise UnsupportedCondition(
                "noncommensurate powers must form one homogeneous triple"
            )
        from .exam_homogeneous import normalize as homogeneous

        base, g, coefficients, divisor = homogeneous(powers, True, anchor="last")
        return base, g, sum(c * T**p for c, p in zip(coefficients, (2, 1, 0))), divisor
    exponents = []
    coefficients = []
    for coefficient, base, exponent in powers:
        conversion = sp.cancel(sp.expand_log(sp.log(base) / sp.log(basis)))
        if conversion.is_Rational is not True:
            raise UnsupportedCondition(
                "all bases must be exact powers of a common base"
            )
        exponent = sp.expand(conversion * exponent)
        offset = exponent.subs(X, 0)
        if offset.is_Rational is not True or abs(offset) > 100:
            raise UnsupportedCondition(
                "a constant exponential shift exceeds the reviewed range"
            )
        coefficients.append(coefficient * basis**offset)
        exponents.append(exponent - offset)
    if constant != 0:
        exponents.append(sp.Integer(0))
        coefficients.append(constant)
    origin = exponents[0]
    different = next((e for e in exponents if e != origin), None)
    if different is None:
        raise UnsupportedCondition("a nonconstant exponential polynomial is required")
    primitive = (
        sp.Poly(different - origin, X).clear_denoms(convert=True)[1].primitive()[1]
    )
    direction = primitive.as_expr() if primitive.LC() > 0 else -primitive.as_expr()
    coordinates = [sp.cancel((e - origin) / direction) for e in exponents]
    if any(q.is_Rational is not True for q in coordinates):
        raise UnsupportedCondition(
            "the exponent polynomials must lie on one affine line"
        )
    denominator = lcm(*(int(q.q) for q in coordinates))
    step = sp.Rational(
        reduce(gcd, (abs(int(q * denominator)) for q in coordinates)), denominator
    )
    lowest = min(coordinates)
    divisor_exponent = sp.expand(origin + lowest * direction)
    degrees = [(q - lowest) / step for q in coordinates]
    if any(d.is_Integer is not True or not 0 <= d <= 4 for d in degrees):
        raise UnsupportedCondition(
            "the normalized exponential degree must be at most four"
        )
    if abs(step) > 100:
        raise UnsupportedCondition("the common-base step exceeds the reviewed range")
    base = basis**step
    g = direction
    if base.is_Rational is not True:
        base = basis
        g = step * direction
    if max(degrees) == 1:
        g, coefficients = linear_shift(powers, basis, exponents, coefficients, degrees)
        base = basis
    polynomial = sp.expand(sum(c * T ** int(d) for c, d in zip(coefficients, degrees)))
    if any(c.is_Rational is not True for c in sp.Poly(polynomial, T).all_coeffs()):
        raise UnsupportedCondition(
            "the normalized polynomial must have rational coefficients"
        )
    divisor = (basis, divisor_exponent) if divisor_exponent != 0 else None
    return base, g, polynomial, divisor


def linear_shift(powers, basis, exponents, coefficients, degrees):
    moving = [(c, e) for c, e in zip(coefficients, exponents) if e != 0]
    if not moving:
        raise UnsupportedCondition("the common exponential factor is missing")
    g = moving[0][1]
    offsets = [
        sp.expand(sp.cancel(sp.expand_log(sp.log(b) / sp.log(basis))) * e - g)
        for _, b, e in powers
    ]
    if any(v.free_symbols for v in offsets):
        raise UnsupportedCondition(
            "the linear exponential powers must share one polynomial part"
        )
    shift = min(offsets)
    g += shift
    coefficients = [c / basis**shift if d else c for c, d in zip(coefficients, degrees)]
    return g, coefficients
