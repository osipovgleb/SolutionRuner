"""Quadratic substitution in powers with a shared rational exponent."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exponential_inequality_common_base import common_base, read_terms, vector, weight
from .exponential_inequality_quadratic import (
    power_stage,
    power_terms,
    rational_gcd,
    scaled,
)
from .rational_inequality import set_latex
from .rational_inequality_methods import terms
from .rational_inequality_parser import X, checked, polynomial
from .rational_substitution_preimages import branches, comparison, excluded_points


def normalize(powers, constant):
    base = common_base([b for _, b, _ in powers])
    effective = [sp.cancel(weight(b, vector(base)) * g) for _, b, g in powers]
    reference = effective[0]
    derivative = sp.diff(reference, X)
    if derivative == 0:
        raise UnsupportedCondition("a nonconstant rational exponent is required")
    ratios = [sp.cancel(sp.diff(g, X) / derivative) for g in effective]
    if any(r.is_Rational is not True or r == 0 for r in ratios):
        raise UnsupportedCondition("all rational exponents must share one substitution")
    numerator, denominator = sp.fraction(reference)
    if polynomial(numerator).degree() > 2 or polynomial(denominator).degree() not in (
        1,
        2,
    ):
        raise UnsupportedCondition(
            "the reviewed rational exponent has degree at most two"
        )
    anchor = next((p for p in (0, 1, -1) if denominator.subs(X, p) != 0), None)
    if anchor is None:
        raise UnsupportedCondition("a finite normalization anchor is required")
    content = rational_gcd(ratios)
    exponent = sp.cancel(checked(content * (reference - reference.subs(X, anchor))))
    coefficients = {0: constant}
    for (coefficient, _, _), value, ratio in zip(powers, effective, ratios):
        degree = ratio / content
        offset = sp.cancel(value - degree * exponent)
        if (
            degree.is_Integer is not True
            or abs(degree) > 4
            or offset.is_Rational is not True
        ):
            raise UnsupportedCondition(
                "small integer degrees and rational offsets are required"
            )
        coefficients[int(degree)] = coefficients.get(int(degree), 0) + scaled(
            coefficient, base, offset
        )
    return base, exponent, {k: v for k, v in coefficients.items() if v != 0}


@dataclass(frozen=True)
class RationalPower:
    formula: str
    operator: str
    original: object
    powers: tuple
    constant: sp.Expr
    base: sp.Expr
    exponent: sp.Expr
    coefficients: tuple
    multiply_degree: int
    stage: object
    positive_solution: object
    poles: tuple
    domain: object
    branches: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def inverse(base, exponent, bound, operator):
    _, back = back_substitute(base, X, (bound,))
    if len(back) != 1 or back[0][1].is_Rational is not True:
        raise UnsupportedCondition(
            "the rational inverse needs an exact rational log level"
        )
    return comparison(exponent - back[0][1], operator)


def analyze(formula):
    left, right, denominators, operator = read_terms(formula)
    powers, constant = power_terms(terms(left) + terms(right, -1))
    base, exponent, coefficients = normalize(powers, constant)
    multiply_degree, stage = power_stage(coefficients, operator)
    positive = stage.solution.intersect(sp.Interval.open(0, sp.oo))
    poles = excluded_points(denominators)
    domain = sp.S.Reals - sp.FiniteSet(*poles)
    parts = branches(
        positive,
        domain,
        lambda bound, op: inverse(base, exponent, bound, op),
        positive=True,
    )
    return RationalPower(
        formula,
        operator,
        left.value - right.value,
        powers,
        constant,
        base,
        exponent,
        tuple(sorted(coefficients.items())),
        multiply_degree,
        stage,
        positive,
        poles,
        domain,
        parts,
        sp.Union(*(b.solution for b in parts)),
    )
