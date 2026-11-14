"""Strict three-root comparison with the source's redundant cubic constraint."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_rationalization import answer
from .radical_inequality_parser import RadicalParser
from .rational_inequality_parser import polynomial
from .rational_substitution_preimages import comparison, excluded_points


@dataclass(frozen=True)
class RootComparison:
    left: sp.Expr
    numerator: sp.Expr
    denominator: sp.Expr
    poles: tuple
    domain: object
    stage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    parts = re.split(r"(\\(?:lt|gt|leq?|geq?)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in ("<", r"\lt"):
        raise UnsupportedCondition(
            "a strict increasing three-root comparison is required"
        )
    roots, denominators = {}, []
    left, right = (
        RadicalParser(part, denominators, radicands=roots).parse()
        for part in (parts[0], parts[2])
    )
    if (
        left.kind != "root"
        or right.kind != "divide"
        or any(child.kind != "root" for child in right.children)
    ):
        raise UnsupportedCondition(
            "one root must be compared to a quotient of two roots"
        )
    L = roots[left.value]
    C, B = (roots[child.value] for child in right.children)
    if (
        len(roots) != 3
        or polynomial(L).degree() != 1
        or polynomial(B).degree() != 1
        or polynomial(C).degree() != 3
    ):
        raise UnsupportedCondition("two affine roots and one cubic root are required")
    # The root in the quotient is handled by B > 0; keep every other source pole.
    rational_denominators = [d for d in denominators if d != right.children[1].value]
    poles = excluded_points(rational_denominators)
    domain = comparison(L, ">=").solution.intersect(comparison(B, ">").solution)
    domain -= sp.FiniteSet(*poles)
    stage = comparison(sp.expand(C - L * B), ">")
    solution = domain.intersect(stage.solution)
    # On this set L*B >= 0 and C > L*B, hence C > 0. No cubic-domain solver.
    return RootComparison(L, C, B, poles, domain, stage, solution)
