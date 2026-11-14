"""Compare square-root differences by monotonicity, including a zero conjugate."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_rationalization import answer
from .radical_inequality_domains import domain
from .radical_inequality_factor import normalized_stage
from .radical_inequality_parser import RadicalParser
from .rational_inequality import OPERATORS
from .rational_inequality_parser import X, checked, polynomial
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class RootDifference:
    square: sp.Expr
    other: sp.Expr
    denominator: sp.Expr
    square_stage: object
    other_stage: object
    constraints: object
    stage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    parts = re.split(r"(\\(?:lt|gt|leq?|geq?)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or OPERATORS.get(parts[1]) != "<=":
        raise UnsupportedCondition(
            "one complete nonpositive root-difference quotient is required"
        )
    radicands, denominators = {}, []
    left, right = (
        RadicalParser(p, denominators, radicands=radicands).parse()
        for p in (parts[0], parts[2])
    )
    if right.value != 0 or left.kind != "divide" or len(radicands) != 2:
        raise UnsupportedCondition(
            "two complete roots over a rational denominator and a zero bound are required"
        )
    numerator, denominator = left.children
    if numerator.kind != "subtract" or any(
        c.kind != "root" for c in numerator.children
    ):
        raise UnsupportedCondition(
            "the whole numerator must be the difference of two roots"
        )
    P, Q = (radicands[c.value] for c in numerator.children)
    D = checked(denominator.value)
    p, q = polynomial(P), polynomial(Q)
    if (
        p.degree() != 2
        or p.LC() != 1
        or sp.discriminant(P, X) != 0
        or q.degree() != 2
        or sp.discriminant(Q, X) <= 0
        or polynomial(P - Q).degree() != 1
        or polynomial(D).degree() != 2
    ):
        raise UnsupportedCondition(
            "a monic square, a quadratic with distinct real zeros and an affine difference are required"
        )
    constraints = domain(radicands, denominators)
    square_stage = comparison(P, ">=")
    other_stage = comparison(Q, ">=")
    stage = normalized_stage((P - Q) / D, "<=", constraints.rational_denominators)
    solution = stage.solution.intersect(constraints.values)
    if square_stage.solution != sp.S.Reals or solution != stage.solution.intersect(
        other_stage.solution
    ):
        raise UnsupportedCondition(
            "the nonnegative square must impose no extra restriction beyond the original poles"
        )
    return RootDifference(
        P, Q, D, square_stage, other_stage, constraints, stage, solution
    )
