"""Prove both reciprocal-sum substitution and nonnegative square identities."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .logarithm_rationalization import answer
from .logarithm_variable_comparison import strict_polynomial
from .rational_inequality_parser import X, polynomial
from .rational_inequality_roots import real_roots
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class ReciprocalSquare:
    base: sp.Expr
    argument: sp.Expr
    coefficient: sp.Expr
    constant: sp.Expr
    domain: object
    outer_stage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    pieces = re.split(
        r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula.removesuffix(".")
    )
    if len(pieces) != 3 or pieces[1] not in (r"\le", r"\leq"):
        raise UnsupportedCondition(
            "one complete nonstrict reciprocal-square inequality is required"
        )
    equation = re.sub(
        r"(\\log_(?:\{[^{}]+\}|[2-9])(?:\^\{?2\}?)?)\s*([0-9]+)(?!\d)",
        r"\1(\2)",
        pieces[0] + "=" + pieces[2],
    )
    atoms, expression = read_equation(
        equation,
        extended=True,
        argument_reader=strict_polynomial,
        argument_powers=True,
    )
    if len(atoms) != 4 or any(a.root or a.denominator for a in atoms):
        raise UnsupportedCondition(
            "four complete polynomial-argument logarithms are required"
        )
    first, inverse, square, last = atoms
    B, A = first.base, first.argument
    if (
        B.is_Integer is not True
        or not 2 <= B <= 10
        or polynomial(A).degree() != 1
        or inverse.base != A
        or inverse.argument != B
        or square.base != B
        or sp.expand(square.argument - A**2) != 0
        or last.base != A
        or last.argument != B**2
    ):
        raise UnsupportedCondition(
            "the complete reciprocal pair and both doubled-log arguments must agree"
        )
    z = sp.Symbol("z", real=True)
    converted = sp.cancel(
        expression.subs(
            {
                first.symbol: z,
                inverse.symbol: 1 / z,
                square.symbol: 2 * z,
                last.symbol: 2 / z,
            },
            simultaneous=True,
        )
    )
    numerator = sp.cancel(converted * z**2)
    if numerator.free_symbols - {z} or not numerator.is_polynomial(z):
        raise UnsupportedCondition(
            "all variable dependence must belong to the reciprocal logarithms"
        )
    p = sp.Poly(numerator, z)
    c, d = -p.nth(3), p.nth(2)
    if (
        c not in (2, 4)
        or d != 2 * c - 2
        or sp.cancel(converted - (z**2 + z**-2 - c * (z + 1 / z) + d)) != 0
    ):
        raise UnsupportedCondition(
            "the whole expression must prove one of the two nonnegative square identities"
        )
    outer = comparison(X**2 - c * X + d - 2, "<=")
    attainable = sp.Union(sp.Interval(-sp.oo, -2), sp.Interval(2, sp.oo))
    if outer.solution.intersect(attainable) != sp.FiniteSet(2):
        raise UnsupportedCondition(
            "the reciprocal sum must force exactly the attainable endpoint two"
        )
    domain = comparison(A, ">").solution - sp.FiniteSet(*real_roots(A - 1))
    solution = comparison(A - B, "=").solution.intersect(domain)
    return ReciprocalSquare(B, A, c, d, domain, outer, solution)
