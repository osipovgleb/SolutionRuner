"""Certify positive numerator factors and exact six-term exponential groupings."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exponential_inequality_common_base import read_terms
from .exponential_inequality_quadratic import (
    analyze_sum,
    power_stage,
    power_terms,
    read_power_sum,
    scaled,
)
from .rational_inequality import analyze, set_latex
from .rational_inequality_methods import terms
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION


@dataclass(frozen=True)
class FractionPower:
    formula: str
    operator: str
    original: sp.Expr
    numerator: object
    denominator: sp.Expr
    negative_root: sp.Expr
    positive_root: sp.Expr
    level: sp.Expr
    stage: object

    @property
    def solution(self):
        return self.stage.solution

    @property
    def answer(self):
        return set_latex(self.solution)


def linear_denominator(formula):
    left, right, denominators, operator = read_terms(formula)
    if left.kind != "divide" or right.value != 0:
        raise UnsupportedCondition(
            "one exponential numerator over an affine denominator is required"
        )
    numerator, denominator = left.children
    d = denominator.value
    p = polynomial(d)
    if p.degree() != 1 or any(c.is_Rational is not True for c in p.all_coeffs()):
        raise UnsupportedCondition("the original denominator must be rational affine")
    if any(
        v.free_symbols and v != d and v.is_positive is not True for v in denominators
    ):
        raise UnsupportedCondition(
            "every additional original denominator must be proved positive"
        )
    powers, constant = power_terms(terms(numerator))
    a = analyze_sum(formula, operator, numerator.value, powers, constant)
    if (
        a.multiply_degree != 1
        or len(a.stage.zeros) != 2
        or polynomial(a.stage.original).LC() <= 0
    ):
        raise UnsupportedCondition(
            "the parent needs a positive quadratic after multiplying by one positive power"
        )
    lo, hi = a.stage.zeros
    if lo.is_negative is not True or hi.is_positive is not True or len(a.back) != 1:
        raise UnsupportedCondition(
            "the numerator must have one negative and one positive power root"
        )
    level = a.back[0][1]
    if level.is_Rational is not True:
        raise UnsupportedCondition(
            "the reviewed rationalization needs an exact rational logarithmic level"
        )
    stage = analyze(
        r"\frac{"
        + sp.latex(a.exponent - level)
        + "}{"
        + sp.latex(d)
        + "}"
        + RELATION[operator]
        + "0"
    )
    if stage.poles != (-p.nth(0) / p.nth(1),):
        raise UnsupportedCondition(
            "rationalization must retain the original affine pole"
        )
    return FractionPower(formula, operator, left.value, a, d, lo, hi, level, stage)


def factor_grid(coefficients):
    matches = []
    for base in coefficients:
        for other in coefficients:
            if not other > base > 1:
                continue
            grid = (base**2 * other, base**3, base * other, base**2, other, base)
            if len(set(grid)) != 6 or set(grid) != set(coefficients):
                continue
            a, b, c = (coefficients[grid[i]] for i in (0, 2, 4))
            if a > 0 and tuple(coefficients[grid[i]] for i in (1, 3, 5)) == (
                -a,
                -b,
                -c,
            ):
                matches.append((base, other, (a, b, c)))
    if len(matches) != 1:
        raise UnsupportedCondition(
            "the six coefficients must form one exact quadratic grouping"
        )
    return matches[0]


@dataclass(frozen=True)
class GroupedQuadratic:
    formula: str
    operator: str
    original: sp.Expr
    powers: tuple
    base: sp.Expr
    other: sp.Expr
    coefficients: tuple
    quadratic: object
    back: tuple
    roots: tuple
    stage: object

    @property
    def solution(self):
        return self.stage.solution

    @property
    def answer(self):
        return set_latex(self.solution)


def grouped_quadratic(formula):
    operator, original, powers, constant = read_power_sum(formula)
    if len(powers) != 6 or constant != 0:
        raise UnsupportedCondition(
            "the parent grouping needs six powers and no extra constant"
        )
    coefficients = {}
    for c, base, g in powers:
        p = polynomial(g)
        if p.degree() != 1:
            raise UnsupportedCondition("the six grouped powers need affine exponents")
        b = scaled(sp.Integer(1), base, p.nth(1))
        value = scaled(c, base, p.nth(0))
        coefficients[b] = coefficients.get(b, 0) + value
    base, other, values = factor_grid(coefficients)
    _, quadratic = power_stage(dict(zip((2, 1, 0), values)), operator)
    if len(quadratic.zeros) != 2 or any(
        r.is_positive is not True for r in quadratic.zeros
    ):
        raise UnsupportedCondition("the grouped quadratic needs two positive roots")
    roots, back = back_substitute(base, X, quadratic.zeros)
    if len(roots) != 2 or any(r.is_Rational is not True for r in roots):
        raise UnsupportedCondition(
            "the grouped parent needs exact rational critical exponents"
        )
    stage = analyze(
        sp.latex(X * sp.prod(X - r for r in roots)) + RELATION[operator] + "0"
    )
    return GroupedQuadratic(
        formula,
        operator,
        original,
        powers,
        base,
        other,
        values,
        quadratic,
        tuple(back),
        tuple(roots),
        stage,
    )


ANALYSES = {
    "linear_denominator": linear_denominator,
    "grouped_quadratic": grouped_quadratic,
}
