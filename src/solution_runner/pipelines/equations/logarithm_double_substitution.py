"""Recognize a quadratic in a quadratic of one logarithm using exact intervals."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_rational_substitution import (
    RationalLogSubstitution,
    inverse,
    read_input,
)
from .logarithm_rationalization import parts
from .rational_inequality import analyze as rational
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class DoubleSubstitution:
    logarithm: RationalLogSubstitution
    shift: sp.Expr
    linear: sp.Expr
    constant: sp.Expr
    inner: sp.Expr
    outer_stage: object

    @property
    def answer(self):
        return self.logarithm.answer


def analyze(formula):
    base, terms, transformed = read_input(formula.removesuffix("."))
    stage = rational(transformed)
    p = polynomial(stage.original)
    if (
        stage.operator != "<"
        or p.degree() != 4
        or p.LC() != 1
        or stage.poles
        or any(t.linear != X for t in terms)
    ):
        raise UnsupportedCondition(
            "a monic quartic in one complete logarithm of x is required"
        )
    shift = -p.nth(3) / 2
    linear = p.nth(2) - shift**2
    constant = p.nth(0)
    inner = X**2 - shift * X
    if (
        shift.is_Integer is not True
        or not 1 <= shift <= 8
        or sp.expand(inner**2 + linear * inner + constant) != stage.original
        or len(stage.zeros) != 4
        or any(v.is_Integer is not True or abs(v) > 8 for v in stage.zeros)
    ):
        raise UnsupportedCondition(
            "the complete quartic must be a reviewed quadratic in the same inner expression"
        )
    outer = comparison(X**2 + linear * X + constant, "<")
    intervals = parts(stage.solution)
    if len(intervals) != 2 or any(
        not isinstance(part, sp.Interval) for part in intervals
    ):
        raise UnsupportedCondition(
            "the reviewed parent needs two bounded logarithm intervals"
        )
    images = tuple(
        (part, sp.Interval.open(inverse(base, part.start), inverse(base, part.end)))
        for part in intervals
    )
    endpoints = tuple((point, inverse(base, point)) for point in stage.points)
    logarithm = RationalLogSubstitution(
        base,
        terms,
        transformed,
        stage,
        images,
        endpoints,
        sp.Interval.open(0, sp.oo),
        sp.Union(*(image for _, image in images)),
    )
    return DoubleSubstitution(logarithm, shift, linear, constant, inner, outer)
