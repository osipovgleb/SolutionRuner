"""Certify two positive coefficients before removing a shared logarithm factor."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_inequality import rational_polynomial
from .logarithm_absolute_fraction_input import read
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_substitution_preimages import comparison, excluded_points


@dataclass(frozen=True)
class LogAbsoluteFraction:
    base: sp.Expr
    style: str | None
    argument: sp.Expr
    coefficient: sp.Expr
    right_scalar: sp.Expr
    degree: int
    denominator: sp.Expr
    center: sp.Expr
    positive_coefficient: sp.Expr
    negative_numerator: sp.Expr
    poles: tuple
    domain: object
    stage: object
    cases: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def positivity(coefficient, scale, denominator, center):
    positive = sp.cancel((coefficient - scale) / denominator)
    p = rational_polynomial(positive, 1)
    negative = sp.expand(coefficient + scale)
    q = rational_polynomial(negative, 2)
    if (
        p.LC() <= 0
        or positive.subs(X, center) < 0
        or q.LC() <= 0
        or sp.discriminant(q) >= 0
    ):
        raise UnsupportedCondition(
            "the parent's two coefficients must be strictly positive on their full sign intervals"
        )
    return positive, negative


def analyze(formula):
    first, second, denominator, denominators, operator = read(formula)
    C, A, base, style = first
    scalar, power, other_base, _ = second
    d = rational_polynomial(denominator, 1)
    rational_polynomial(C, 2)
    rational_polynomial(A, 2)
    if (
        operator != ">="
        or base != other_base
        or base.is_Rational is not True
        or base <= 1
        or d.LC() <= 0
    ):
        raise UnsupportedCondition(
            "one increasing log base, positive affine denominator slope and parent comparison are required"
        )
    if (
        not isinstance(power, sp.Pow)
        or power.exp not in (2, 4, 6, 8)
        or sp.expand(power.base + A) != 0
        or scalar.is_Rational is not True
        or scalar <= 0
    ):
        raise UnsupportedCondition(
            "the right logarithm must have the complete opposite quadratic raised to a bounded even power"
        )
    degree = int(power.exp)
    scale = scalar * degree
    center = -d.nth(0) / d.nth(1)
    positive, negative = positivity(C, scale, denominator, center)
    original_denominators = (*denominators, denominator)
    poles = excluded_points(original_denominators)
    domain = comparison(A, ">", denominators=original_denominators).solution
    stage = comparison(A - 1, ">=")
    cases = tuple(
        (
            sign,
            stage.solution.intersect(domain).intersect(
                comparison(denominator, op).solution
            ),
        )
        for sign, op in ((1, ">"), (-1, "<"))
    )
    solution = sp.Union(*(s for _, s in cases))
    return LogAbsoluteFraction(
        base,
        style,
        A,
        C,
        scalar,
        degree,
        denominator,
        center,
        positive,
        negative,
        poles,
        domain,
        stage,
        cases,
        solution,
    )
