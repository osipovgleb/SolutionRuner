"""Reuse exact comparisons for reciprocal modulus powers and signed exponents."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_input import AbsolutePowerReader
from .exponential_inequality_common_base import read_terms
from .rational_inequality import set_latex
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison, excluded_points


def rational_polynomial(value, degree):
    p = polynomial(value)
    if p.degree() != degree or any(c.is_Rational is not True for c in p.all_coeffs()):
        raise UnsupportedCondition(
            "the whole parent polynomial degree and rational coefficients are required"
        )
    return p


def read(formula):
    values = {}
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: AbsolutePowerReader(text, values)
    )
    if len(values) != 1:
        raise UnsupportedCondition("one shared polynomial modulus is required")
    symbol, argument = next(iter(values.items()))
    return left, right, denominators, operator, symbol, argument


@dataclass(frozen=True)
class ReciprocalPowers:
    argument: sp.Expr
    exponent: sp.Expr
    poles: tuple
    stage: object
    branches: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def reciprocal(formula):
    left, right, denominators, operator, symbol, argument = read(formula)
    if left.kind != "add" or right.value != 2 or operator != "<=":
        raise UnsupportedCondition(
            "the parent compares two reciprocal positive powers with two"
        )
    powers = left.children
    if any(
        p.kind != "exponential"
        or p.children[0].kind != "absolute"
        or p.children[0].value != symbol
        for p in powers
    ):
        raise UnsupportedCondition(
            "both complete powers must have the same modulus base"
        )
    exponent, other = (p.children[1].value for p in powers)
    rational_polynomial(argument, 1)
    rational_polynomial(exponent, 1)
    if sp.expand(exponent + other) != 0:
        raise UnsupportedCondition("the complete exponents must be exact opposites")
    poles = excluded_points((*denominators, argument))
    stage = comparison(X + 1 / X - 2, "<=")
    branches = tuple(
        comparison(value, "=") for value in (argument - 1, argument + 1, exponent)
    )
    solution = sp.Union(*(s.solution for s in branches)) - sp.FiniteSet(*poles)
    return ReciprocalPowers(argument, exponent, poles, stage, branches, solution)


@dataclass(frozen=True)
class SignedExponent:
    base: sp.Expr
    exponent: sp.Expr
    symbol: sp.Symbol
    operator: str
    exponent_operator: str
    cases: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def signed_exponent(formula):
    left, right, denominators, operator, symbol, argument = read(formula)
    if left.kind != "exponential" or right.value != 1 or argument != X:
        raise UnsupportedCondition(
            "one numeric power compared with one and a modulus of x is required"
        )
    base, exponent = (c.value for c in left.children)
    if (
        base.is_Rational is not True
        or base <= 0
        or base == 1
        or max(base.p, base.q) > 10**6
    ):
        raise UnsupportedCondition(
            "a bounded positive rational base other than one is required"
        )
    if not exponent.has(symbol):
        raise UnsupportedCondition("the complete exponent must contain the modulus")
    exponent_operator = (
        operator if base > 1 else {"<=": ">=", "<": ">", ">=": "<=", ">": "<"}[operator]
    )
    cases = []
    for sign, domain in ((1, sp.Interval(0, sp.oo)), (-1, sp.Interval(-sp.oo, 0))):
        value = sp.cancel(exponent.subs(symbol, sign * X))
        numerator, denominator = sp.fraction(value)
        rational_polynomial(numerator, 2)
        rational_polynomial(denominator, 2)
        stage = comparison(
            value,
            exponent_operator,
            denominators=tuple(d.subs(symbol, sign * X) for d in denominators),
        )
        cases.append((sign, stage, stage.solution.intersect(domain)))
    solution = sp.Union(*(s for _, _, s in cases))
    return SignedExponent(
        base, exponent, symbol, operator, exponent_operator, tuple(cases), solution
    )
