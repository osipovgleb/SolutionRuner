"""Reuse positive-power solving for homogeneous, collected and grouped terms."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_homogeneous import normalize
from .exponential_inequality_common_base import common_base, vector, weight
from .exponential_inequality_quadratic import (
    PositivePower,
    read_power_sum,
    scaled,
    solve_positive,
)
from .rational_inequality import analyze, set_latex
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION


def homogeneous(formula):
    operator, original, powers, constant = read_power_sum(formula)
    if len(powers) != 3 or constant != 0:
        raise UnsupportedCondition(
            "three homogeneous powers and no constant are required"
        )
    ordered = tuple(sorted(powers, key=lambda term: term[1], reverse=True))
    base, exponent, values, divisor = normalize(ordered, False)
    coefficients = dict(zip((2, 1, 0), values))
    return PositivePower(
        formula,
        operator,
        original,
        ordered,
        constant,
        base,
        exponent,
        tuple(sorted(coefficients.items())),
        *solve_positive(base, exponent, coefficients, operator),
        divisor=divisor,
    )


def collected(formula):
    operator, original, powers, constant = read_power_sum(formula)
    if not 2 <= len(powers) <= 4 or constant == 0:
        raise UnsupportedCondition(
            "two to four collected powers and a nonzero bound are required"
        )
    base = common_base([b for _, b, _ in powers])
    exponents = [sp.expand(weight(b, vector(base)) * g) for _, b, g in powers]
    polys = [polynomial(g) for g in exponents]
    if any(p.degree() != 1 for p in polys) or len({p.nth(1) for p in polys}) != 1:
        raise UnsupportedCondition(
            "the collected exponents must have the same affine slope"
        )
    exponent = polys[0].nth(1) * X + min(p.nth(0) for p in polys)
    coefficient = sum(
        scaled(c, base, g - exponent) for (c, _, _), g in zip(powers, exponents)
    )
    coefficients = {0: constant, 1: coefficient}
    return PositivePower(
        formula,
        operator,
        original,
        powers,
        constant,
        base,
        exponent,
        tuple(sorted(coefficients.items())),
        *solve_positive(base, exponent, coefficients, operator, degree=1),
    )


@dataclass(frozen=True)
class Grouped:
    formula: str
    operator: str
    original: object
    powers: tuple
    constant: sp.Expr
    bases: tuple
    bounds: tuple
    exponent: sp.Expr
    roots: tuple
    stage: object

    @property
    def solution(self):
        return self.stage.solution

    @property
    def answer(self):
        return set_latex(self.solution)


def grouped(formula):
    operator, original, powers, constant = read_power_sum(formula)
    if len(powers) != 3 or len({g for _, _, g in powers}) != 1:
        raise UnsupportedCondition("three powers must share the grouped exponent")
    exponent = powers[0][2]
    ordered = tuple(sorted(powers, key=lambda term: term[1], reverse=True))
    (c, product, _), (ca, a, _), (cb, b, _) = ordered
    if (
        polynomial(exponent).degree() != 1
        or c != 1
        or a <= 1
        or b <= 1
        or product != a * b
    ):
        raise UnsupportedCondition(
            "the parent grouping needs a monic product of two increasing bases"
        )
    u, v = -cb, -ca
    if u <= 0 or v <= 0 or constant != u * v:
        raise UnsupportedCondition(
            "the scalar terms must form the same exact grouped product"
        )
    roots = weight(u, vector(a)), weight(v, vector(b))
    stage = analyze(
        sp.latex((exponent - roots[0]) * (exponent - roots[1]))
        + RELATION[operator]
        + "0"
    )
    return Grouped(
        formula,
        operator,
        original,
        ordered,
        constant,
        (a, b),
        (u, v),
        exponent,
        roots,
        stage,
    )


ANALYSES = {
    "homogeneous": homogeneous,
    "grouped_product": grouped,
    "collected_power": collected,
}
