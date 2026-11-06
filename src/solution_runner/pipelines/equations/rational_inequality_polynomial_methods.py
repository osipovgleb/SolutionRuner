"""Reviewed common-denominator methods preserving polynomial factors and holes."""

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality_methods import Step, fraction, latex, terms
from .rational_inequality_parser import X, polynomial


def collect(node):
    whole = sp.Integer(0)
    fractions = []
    for sign, term in terms(node):
        if term.kind == "divide":
            numerator, denominator = (child.value for child in term.children)
            fractions.append((sign * numerator, denominator))
        elif term.value.is_polynomial(X):
            whole += sign * term.value
        else:
            raise UnsupportedCondition(
                "only polynomial terms and explicit fractions are supported"
            )
    return sp.expand(whole), fractions


def one_fraction(a):
    whole, values = collect(a.left)
    if len(values) != 1 or not a.right.value.is_polynomial(X):
        raise UnsupportedCondition(
            "one explicit fraction and a polynomial bound are required"
        )
    numerator, denominator = values[0]
    if polynomial(denominator).degree() != 1:
        raise UnsupportedCondition("the source denominator must be affine")
    return whole, numerator, denominator


def quadratic_right(a):
    whole, n, d = one_fraction(a)
    if (
        whole != 0
        or polynomial(n).degree() != 2
        or polynomial(a.right.value).degree() > 1
    ):
        raise UnsupportedCondition(
            "a quadratic-over-affine fraction and an affine bound are required"
        )
    corrected = sp.expand(n - a.right.value * d)
    if polynomial(corrected).degree() != 2:
        raise UnsupportedCondition("moving the bound must leave a quadratic numerator")
    return [], [
        Step(
            fraction(n, d) + "-" + fraction(sp.expand(a.right.value * d), d), a.original
        ),
        Step(fraction(corrected, d), a.original),
    ]


def cubic_cancel(a):
    whole, n, d = one_fraction(a)
    if (
        polynomial(whole).degree() != 2
        or polynomial(n).degree() != 3
        or a.right.value.free_symbols
    ):
        raise UnsupportedCondition(
            "a quadratic polynomial, cubic numerator and constant bound are required"
        )
    corrected = sp.expand(whole * d + n - a.right.value * d)
    if polynomial(corrected).degree() != 2:
        raise UnsupportedCondition(
            "the cubic terms must cancel to a quadratic numerator"
        )
    common = (
        fraction(sp.Mul(whole, d, evaluate=False), d)
        + "+"
        + fraction(n, d)
        + "-"
        + fraction(sp.Mul(a.right.value, d, evaluate=False), d)
    )
    return [], [
        Step(common, a.original),
        Step(fraction(corrected, d), a.original),
        Step(fraction(sp.factor(corrected), d), a.original),
    ]


def square_zero(a):
    whole, n, d = one_fraction(a)
    corrected = sp.expand(n - a.right.value * d)
    p = polynomial(corrected)
    if (
        polynomial(whole).degree() != 3
        or polynomial(n).degree() != 2
        or a.right.value.free_symbols
        or p.degree() != 2
        or p.nth(0) != 0
        or p.nth(1) != 0
    ):
        raise UnsupportedCondition(
            "subtracting the bound must leave a nonzero multiple of x squared"
        )
    combined = sp.expand(whole * d + corrected)
    q = polynomial(combined)
    if q.degree() != 4 or q.nth(0) != 0 or q.nth(1) != 0 or q.nth(2) == 0:
        raise UnsupportedCondition(
            "the common numerator must retain a zero of multiplicity two"
        )
    return [], [
        Step(latex(whole) + "+" + fraction(corrected, d), a.original),
        Step(fraction(combined, d), a.original),
    ]


def quadratic_denominators(a):
    left, left_values = collect(a.left)
    right, right_values = collect(a.right)
    values = left_values + [(-n, d) for n, d in right_values]
    if (
        left != 0
        or right != 0
        or len(values) != 2
        or len(a.holes) != 1
        or any(
            polynomial(n).degree() > 0 or polynomial(d).degree() != 2 for n, d in values
        )
    ):
        raise UnsupportedCondition(
            "two constant-over-quadratic fractions and one cancelled pole are required"
        )
    if polynomial(sp.gcd(values[0][1], values[1][1])).degree() != 1:
        raise UnsupportedCondition(
            "the two denominators must share exactly one affine factor"
        )
    denominator = sp.factor(sp.lcm([d for _, d in values]))
    pieces = [
        sp.Mul(n, sp.factor(sp.cancel(denominator / d)), evaluate=False)
        for n, d in values
    ]
    numerator = sp.Add(*pieces, evaluate=False)
    expanded = sp.expand(numerator)
    if polynomial(expanded).degree() != 1:
        raise UnsupportedCondition(
            "the common numerator must be affine before cancellation"
        )
    return [], [
        Step("+".join(fraction(n, sp.factor(d)) for n, d in values), a.original),
        Step(fraction(numerator, denominator), a.original),
        Step(fraction(expanded, denominator), a.original),
        Step(fraction(sp.factor(expanded), denominator), a.original),
    ]


METHODS = {
    "quadratic_right": quadratic_right,
    "cubic_cancel": cubic_cancel,
    "square_zero": square_zero,
    "quadratic_denominators": quadratic_denominators,
}
