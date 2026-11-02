"""Certify complete positive monomials before choosing one exponential unit."""

from dataclasses import dataclass

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from ..word_problems.math_common import primitive
from .exam_trigonometric_compile import C, S
from .exam_trigonometric_power_equality import prime_logs

E = sp.Symbol("e", positive=True)
A, B = sp.symbols("a b")


@dataclass(frozen=True)
class PowerUnit:
    base: sp.Expr
    argument: sp.Expr
    polynomial: sp.Expr
    rational: sp.Expr
    divisor: sp.Expr


def affine(exponent, argument):
    numerator = sp.fraction(sp.cancel(exponent - A * argument - B))[0]
    if not numerator.is_polynomial(S, C) or sp.Poly(numerator, S, C).total_degree() > 6:
        return None
    remainder = sp.rem(numerator, S * S + C * C - 1, S)
    solutions = sp.linsolve(sp.Poly(remainder, S, C).coeffs(), (A, B))
    if len(solutions) != 1:
        return None
    a, b = next(iter(solutions))
    if any(v.is_Rational is not True or abs(v) > 1000 or v.q > 100 for v in (a, b)):
        return None
    return a, b


def monomial(term, argument):
    coefficient, vector = sp.S.One, {}
    for factor in sp.Mul.make_args(term):
        if factor.is_Pow and factor.base.is_Rational and factor.exp.free_symbols:
            row = affine(factor.exp, argument)
            if row is None:
                return None
            a, b = row
            coefficient *= factor.base**b
            for prime, n in prime_logs(factor.base).items():
                vector[prime] = vector.get(prime, 0) + a * n
        elif factor.free_symbols or factor.is_real is not True:
            return None
        else:
            coefficient *= factor
    return coefficient, {p: v for p, v in vector.items() if v != 0}


def direction(rows):
    reference = rows[0][1]
    differences = [
        {p: v.get(p, 0) - reference.get(p, 0) for p in v.keys() | reference.keys()}
        for _, v in rows
    ]
    first = next((v for v in differences if any(v.values())), None)
    if first is None:
        return None
    denominator = sp.ilcm(1, *(v.q for v in first.values()))
    integers = {p: v * denominator for p, v in first.items() if v != 0}
    divisor = sp.igcd(0, *integers.values())
    return {p: v / divisor for p, v in integers.items()}


def coordinates(rows, weights, below_one):
    base = sp.prod(sp.Integer(p) ** n for p, n in weights.items())
    if bool(base < 1) != below_one:
        weights = {p: -v for p, v in weights.items()}
        base = 1 / base
    prime = min(weights)
    reference = rows[0][1]
    ratios = [
        (v.get(prime, 0) - reference.get(prime, 0)) / weights[prime] for _, v in rows
    ]
    if any(
        v.get(p, 0) - reference.get(p, 0) != ratio * weights.get(p, 0)
        for (_, v), ratio in zip(rows, ratios, strict=True)
        for p in v.keys() | reference.keys() | weights.keys()
    ):
        return None
    through_origin = all(
        reference.get(p, 0)
        == reference.get(prime, 0) / weights[prime] * weights.get(p, 0)
        for p in reference.keys() | weights.keys()
    )
    if through_origin:
        ratios = [v.get(prime, 0) / weights[prime] for _, v in rows]
        reference = {}
    else:
        index = min(range(len(ratios)), key=ratios.__getitem__)
        offset = ratios[index]
        reference = rows[index][1]
        ratios = [v - offset for v in ratios]
    step = sp.Rational(
        sp.igcd(0, *(v.p for v in ratios)), sp.ilcm(1, *(v.q for v in ratios))
    )
    if not 0 < step <= 100 or step.q > 100:
        return None
    return base, step, ratios, reference


def normalize(expression, argument, *, below_one=False, exponent_multiplier=False):
    terms = sp.Add.make_args(sp.expand(expression))
    if not 2 <= len(terms) <= 6:
        raise UnsupportedCondition(
            "two to six complete exponential monomials are required"
        )
    rows = [monomial(term, argument) for term in terms]
    if any(v is None for v in rows):
        return None
    weights = direction(rows)
    position = coordinates(rows, weights, below_one) if weights else None
    if position is None:
        return None
    base, step, ratios, reference = position
    rational = sp.cancel(
        sp.Add(*(c * E ** (n / step) for (c, _), n in zip(rows, ratios, strict=True)))
    )
    numerator, denominator = sp.fraction(rational)
    if numerator.free_symbols - {E} or not numerator.is_polynomial(E):
        return None
    if sp.degree(numerator, E) != 2 or denominator.free_symbols - {E}:
        return None
    polynomial = (
        primitive(numerator, (E,))
        if all(v.is_Rational for v in sp.Poly(numerator, E).all_coeffs())
        else sp.Poly(numerator, E, extension=True).monic().as_expr()
    )
    unit_base, unit_argument = (
        (base, step * argument) if exponent_multiplier else (base**step, argument)
    )
    divisor = sp.prod(sp.Integer(p) ** (n * argument) for p, n in reference.items())
    return PowerUnit(unit_base, unit_argument, polynomial, rational, divisor)
