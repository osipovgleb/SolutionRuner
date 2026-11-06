"""Reduce affine exponential sums to a polynomial on the positive half-line."""

from dataclasses import dataclass
from functools import reduce
from math import gcd, lcm

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exam_exponential_proof import labels
from .exponential_inequality_common_base import (
    common_base,
    monomial,
    read_terms,
    vector,
    weight,
)
from .rational_inequality import analyze, set_latex
from .rational_inequality_methods import terms
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION


def rational_gcd(values):
    denominator = reduce(lcm, (v.q for v in values))
    numerator = reduce(gcd, (abs(int(v * denominator)) for v in values))
    return sp.Rational(numerator, denominator)


def inverse(solution, mapping, increasing):
    def point(value):
        if value == 0:
            return -sp.oo if increasing else sp.oo
        if value == sp.oo:
            return sp.oo if increasing else -sp.oo
        return mapping[value]

    if isinstance(solution, sp.Union):
        return sp.Union(*(inverse(part, mapping, increasing) for part in solution.args))
    if isinstance(solution, sp.FiniteSet):
        return sp.FiniteSet(*(point(p) for p in solution))
    if isinstance(solution, sp.Interval):
        lo, hi = point(solution.start), point(solution.end)
        return (
            sp.Interval(
                lo, hi, left_open=solution.left_open, right_open=solution.right_open
            )
            if increasing
            else sp.Interval(
                hi, lo, left_open=solution.right_open, right_open=solution.left_open
            )
        )
    if solution == sp.EmptySet:
        return solution
    raise UnsupportedCondition(
        "the positive quadratic must have an exact interval solution"
    )


@dataclass(frozen=True)
class PositivePower:
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
    back: tuple
    solution: object
    divisor: tuple = ()

    def endpoint(self, value):
        return labels(self, number_formatter=sp.latex, preserve_offset=True).get(
            value, sp.latex(value)
        )

    @property
    def answer(self):
        return set_latex(self.solution, endpoint=self.endpoint)


def read_power_sum(formula):
    left, right, denominators, operator = read_terms(formula)
    for d in denominators:
        if d.free_symbols and d.is_positive is not True:
            raise UnsupportedCondition(
                "only proved-positive exponential denominators are supported"
            )
    powers = []
    constant = sp.Integer(0)
    for sign, node in terms(left) + terms(right, -1):
        coefficient, power = monomial(node)
        if power is None:
            constant += sign * coefficient
        else:
            powers.append((sign * coefficient, *power))
    if not 1 <= len(powers) <= 6:
        raise UnsupportedCondition("one to six bounded exponential terms are required")
    return operator, left.value - right.value, tuple(powers), constant


def solve_positive(base, exponent, coefficients, operator, *, degree=2):
    p = polynomial(exponent)
    if (
        base <= 1
        or p.degree() != 1
        or any(c.is_Rational is not True for c in p.all_coeffs())
    ):
        raise UnsupportedCondition(
            "an increasing base and rational affine exponent are required"
        )
    if not coefficients or any(
        c.is_Rational is not True or max(abs(c.p), c.q) > 10**12
        for c in coefficients.values()
    ):
        raise UnsupportedCondition("bounded rational power coefficients are required")
    multiply_degree = max(0, -min(coefficients))
    value = sp.expand(
        sum(c * X ** (k + multiply_degree) for k, c in coefficients.items())
    )
    if multiply_degree > 2 or polynomial(value).degree() != degree:
        raise UnsupportedCondition(
            "the positive-power polynomial must have the reviewed degree"
        )
    stage = analyze(sp.latex(value) + RELATION[operator] + "0")
    positive = sp.Intersection(stage.solution, sp.Interval.open(0, sp.oo))
    _, back = back_substitute(base, exponent, stage.zeros)
    mapping = {t: branch[0] for t, _, branch in back}
    solution = inverse(positive, mapping, p.nth(1) > 0)
    return multiply_degree, stage, positive, tuple(back), solution


def scaled(coefficient, base, offset):
    if abs(offset) > 40 or offset.q > 100:
        raise UnsupportedCondition(
            "the constant power offset exceeds exact arithmetic bounds"
        )
    result = coefficient * base**offset
    if result.is_Rational is not True or max(abs(result.p), result.q) > 10**12:
        raise UnsupportedCondition(
            "the normalized power coefficient must be a bounded rational"
        )
    return result


def analyze_quadratic(formula):
    operator, original, powers, constant = read_power_sum(formula)
    base = common_base([b for _, b, _ in powers])
    reference = vector(base)
    effective = [sp.expand(weight(b, reference) * g) for _, b, g in powers]
    if any(polynomial(g).degree() != 1 for g in effective):
        raise UnsupportedCondition(
            "this inverse substitution requires affine exponents"
        )
    slopes = [polynomial(g).nth(1) for g in effective]
    slope = rational_gcd(slopes) * (-1 if all(v < 0 for v in slopes) else 1)
    exponent = slope * X
    coefficients = {0: constant}
    for (coefficient, _, _), g in zip(powers, effective):
        degree = sp.cancel(polynomial(g).nth(1) / slope)
        offset = g.subs(X, 0)
        coefficient = scaled(coefficient, base, offset)
        if degree.is_Integer is not True or abs(degree) > 4:
            raise UnsupportedCondition(
                "the normalized powers need small integer degrees and rational coefficients"
            )
        coefficients[int(degree)] = coefficients.get(int(degree), 0) + coefficient
    coefficients = {k: v for k, v in coefficients.items() if v != 0}
    return PositivePower(
        formula,
        operator,
        original,
        tuple(powers),
        constant,
        base,
        exponent,
        tuple(sorted(coefficients.items())),
        *solve_positive(base, exponent, coefficients, operator),
    )
