"""Bounded exact Laurent polynomials for integer powers of real variables."""

from fractions import Fraction

import sympy as sp

from ..probability.common import UnsupportedCondition


def checked(poly):
    poly = {k: v for k, v in poly.items() if v}
    if (
        len(poly) > 30
        or any(abs(p) > 1000 for k in poly for _, p in k)
        or any(
            max(abs(v.numerator).bit_length(), v.denominator.bit_length()) > 4096
            for v in poly.values()
        )
    ):
        raise UnsupportedCondition(
            "the Laurent expression exceeds the supported exact range"
        )
    return poly


def add(left, right, sign=1):
    result = dict(left)
    for key, value in right.items():
        result[key] = result.get(key, Fraction(0)) + sign * value
    return checked(result)


def multiply(left, right):
    result = {}
    for a, x in left.items():
        for b, y in right.items():
            powers = dict(a)
            for name, p in b:
                powers[name] = powers.get(name, 0) + p
            key = tuple(sorted((name, p) for name, p in powers.items() if p))
            result[key] = result.get(key, Fraction(0)) + x * y
    return checked(result)


def names(poly):
    return {name for key in poly for name, _p in key}


def power(poly, exponent, nonzero):
    if not poly:
        if exponent > 0:
            return {}
        raise UnsupportedCondition("zero to a nonpositive power is undefined")
    if len(poly) != 1:
        if not 1 <= exponent <= 20:
            raise UnsupportedCondition(
                "polynomial powers need a small positive integer"
            )
        result = {(): Fraction(1)}
        for _ in range(exponent):
            result = multiply(result, poly)
        return result
    key, coefficient = next(iter(poly.items()))
    if exponent <= 0:
        nonzero.update(names(poly))
    return checked(
        {
            tuple((name, p * exponent) for name, p in key if p * exponent): coefficient
            ** exponent
        }
    )


def divide(left, right, nonzero):
    if not right:
        raise UnsupportedCondition("division by zero in a Laurent expression")
    if len(right) != 1:
        raise UnsupportedCondition("the supported Laurent denominator is a monomial")
    nonzero.update(names(right))
    return multiply(left, power(right, -1, nonzero))


def symbolic(poly):
    return sum(
        (
            sp.Rational(v.numerator, v.denominator)
            * sp.prod(sp.Symbol(name, real=True) ** p for name, p in key)
            for key, v in poly.items()
        ),
        sp.Integer(0),
    )


def latex(poly):
    return sp.latex(symbolic(poly))


def exact_value(poly, bindings, nonzero):
    for name in nonzero:
        if name in bindings and bindings[name].is_zero is not False:
            raise UnsupportedCondition(
                "the assigned value violates an original nonzero denominator condition"
            )
    if names(poly) - set(bindings):
        raise UnsupportedCondition(
            "an unassigned variable remains in the Laurent result"
        )
    result = sp.simplify(
        symbolic(poly).subs({sp.Symbol(k, real=True): v for k, v in bindings.items()})
    )
    if result.is_Rational is not True:
        raise UnsupportedCondition("the Laurent result is not an exact rational number")
    return Fraction(int(result.p), int(result.q))
