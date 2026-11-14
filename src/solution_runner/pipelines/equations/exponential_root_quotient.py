"""Factor a whole two-base exponential numerator before imposing a strict root denominator."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_inequality import rational_polynomial
from .exam_exponential import back_substitute
from .exponential_inequality_common_base import vector
from .exponential_inequality_parser import ExponentialParser
from .logarithm_rationalization_input import fraction_parts
from .radical_inequality_parser import RadicalParser
from .rational_inequality import set_latex
from .rational_inequality_parser import RationalParser, X
from .rational_substitution_preimages import comparison, excluded_points


@dataclass(frozen=True)
class ExponentialRootQuotient:
    bases: tuple
    thresholds: tuple
    scale: sp.Expr
    numerator: sp.Expr
    radicand: sp.Expr
    points: tuple
    poles: tuple
    domain: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def factors(value):
    powers = [p for p in value.atoms(sp.Pow) if p.exp.has(X)]
    if len(powers) != 3 or any(
        p.exp != X or p.base.is_Rational is not True or p.base <= 1 for p in powers
    ):
        raise UnsupportedCondition(
            "three whole increasing numeric powers with common exponent x are required"
        )
    bases = sorted(p.base for p in powers)
    for base in bases:
        vector(base)
    A, B, hybrid = bases
    if hybrid != A * B:
        raise UnsupportedCondition(
            "the third base must be the exact product of the two smaller positive bases"
        )
    u, v = sp.symbols("u v", positive=True)
    projected = sp.expand(value.xreplace({A**X: u, B**X: v, hybrid**X: u * v}))
    if projected.free_symbols - {u, v} or not projected.is_polynomial(u, v):
        raise UnsupportedCondition(
            "all variable dependence must belong to the three complete exponential terms"
        )
    p = sp.Poly(projected, u, v)
    if p.degree(u) > 1 or p.degree(v) > 1:
        raise UnsupportedCondition(
            "the whole numerator must be bilinear in the two positive powers"
        )
    a, b, c, d = p.nth(1, 1), p.nth(1, 0), p.nth(0, 1), p.nth(0, 0)
    if (
        any(t.is_Rational is not True for t in (a, b, c, d))
        or not (a > 0 and b < 0 and c < 0 and d > 0)
        or a * d != b * c
    ):
        raise UnsupportedCondition(
            "the complete coefficient identity must prove two increasing affine power factors"
        )
    thresholds = (-c / a, -b / a)
    roots = []
    for base, threshold in zip((A, B), thresholds, strict=True):
        _, back = back_substitute(base, X, (threshold,))
        point = back[0][2][0]
        if point.is_Rational is not True or abs(point) > 99 or point.q > 20:
            raise UnsupportedCondition(
                "the reviewed sign chart requires bounded rational exponential zeros"
            )
        roots.append(point)
    if roots[0] == roots[1]:
        raise UnsupportedCondition(
            "the parent interval chart requires two distinct zeros"
        )
    return (A, B), thresholds, a, tuple(sorted(roots))


def analyze(formula):
    n, d, right, operator = fraction_parts(formula)
    scalar = RationalParser(right)
    if scalar.parse().value != 0 or operator != ">=":
        raise UnsupportedCondition(
            "one complete exponential/root fraction compared nonnegatively with zero is required"
        )
    numerator = ExponentialParser(n)
    value = numerator.parse().value
    root = RadicalParser(d)
    node = root.parse()
    if (
        node.kind != "root"
        or len(root.radicands) != 1
        or node.value not in root.radicands
    ):
        raise UnsupportedCondition(
            "the entire source denominator must be one principal variable square root"
        )
    radicand = root.radicands[node.value]
    if rational_polynomial(radicand, 1).LC() <= 0:
        raise UnsupportedCondition(
            "the root argument must be an increasing affine polynomial"
        )
    bases, thresholds, scale, points = factors(value)
    denominators = (*numerator.denominators, *root.denominators, *scalar.denominators)
    poles = excluded_points(denominators)
    domain = comparison(radicand, ">", denominators=denominators).solution
    nonnegative = sp.Union(
        sp.Interval(-sp.oo, points[0]), sp.Interval(points[1], sp.oo)
    )
    return ExponentialRootQuotient(
        bases,
        thresholds,
        scale,
        value,
        radicand,
        points,
        poles,
        domain,
        nonnegative.intersect(domain),
    )
