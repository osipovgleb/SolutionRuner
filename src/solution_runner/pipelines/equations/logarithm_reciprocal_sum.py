"""Reduce two mutually inverse logarithms, retaining both original bases."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms
from .logarithm_rationalization import answer
from .rational_inequality import analyze as rational
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison, excluded_points
from .variable_logarithm_parser import Atoms, VariableLogarithmParser


@dataclass(frozen=True)
class ReciprocalSum:
    G: sp.Expr
    A: sp.Expr
    poles: tuple
    domain: object
    substitution: object
    equality: object
    negative_stage: object
    negative: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula.removesuffix("."),
        reader=lambda text: VariableLogarithmParser(text, atoms=atoms),
    )
    if len(atoms.values) != 2 or operator != "<=" or right.value != 2:
        raise UnsupportedCondition(
            "two inverse logarithms with sum at most two are required"
        )
    first, second = atoms.values
    G, A = first.base, first.argument
    if (
        left.value != first.symbol + second.symbol
        or sp.cancel(second.base - A) != 0
        or sp.cancel(second.argument - G) != 0
        or any(polynomial(v).degree() != 1 for v in (G, A))
    ):
        raise UnsupportedCondition(
            "the complete sum must exchange two affine bases and arguments"
        )
    poles = excluded_points((*denominators, G - 1, A - 1))
    domain = sp.Intersection(
        comparison(G, ">").solution, comparison(A, ">").solution
    ) - sp.FiniteSet(*poles)
    substitution = rational(r"\frac{(x-1)^2}{x}\le0")
    if substitution.solution != sp.Union(sp.Interval.open(-sp.oo, 0), sp.FiniteSet(1)):
        raise UnsupportedCondition(
            "the reciprocal substitution must preserve its zero exclusion"
        )
    equality = sp.solveset(G - A, X, domain=sp.S.Reals).intersect(domain)
    negative_stage = comparison((G - 1) * (A - 1), "<")
    negative = negative_stage.solution.intersect(domain)
    solution = sp.Union(equality, negative)
    return ReciprocalSum(
        G, A, poles, domain, substitution, equality, negative_stage, negative, solution
    )
