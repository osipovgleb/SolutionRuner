"""Two plotted base cases over the shared exact logarithm rationalization."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms
from .logarithm_single_rationalization import solve_parts
from .rational_inequality import FLIPPED
from .rational_inequality_parser import polynomial
from .rational_inequality_roots import real_roots
from .rational_substitution_preimages import comparison
from .variable_logarithm_parser import Atoms, VariableLogarithmParser


@dataclass(frozen=True)
class BaseCase:
    sign: int
    operator: str
    values: tuple
    stages: tuple
    solution: object


@dataclass(frozen=True)
class RationalBaseCases:
    logarithm: object
    cases: tuple

    @property
    def answer(self):
        return self.logarithm.answer


def analyze(formula):
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula.removesuffix("."),
        reader=lambda text: VariableLogarithmParser(text, atoms=atoms),
    )
    if (
        len(atoms.values) != 1
        or left.kind != "logarithm"
        or left.value != atoms.values[0].symbol
        or right.value not in (0, 1)
    ):
        raise UnsupportedCondition(
            "one whole variable logarithm compared with zero or one is required"
        )
    atom = atoms.values[0]
    B, Q = atom.base, atom.argument
    numerator, denominator = sp.fraction(sp.cancel(Q))
    if (
        polynomial(B).degree() != 2
        or polynomial(B).LC() <= 0
        or any(polynomial(v).degree() > 2 for v in (numerator, denominator))
    ):
        raise UnsupportedCondition(
            "an upward quadratic base and a bounded rational quadratic argument are required"
        )
    a = solve_parts(B, Q, right.value, operator, denominators)
    extra = sp.FiniteSet(*a.poles) - sp.FiniteSet(*real_roots(B - 1))
    cases = []
    for sign, relation in ((1, ">"), (-1, "<")):
        stage = comparison(B - 1, relation)
        op = operator if sign == 1 else FLIPPED[operator]
        allowed = comparison(Q - a.power, op).solution.intersect(a.domains[1]) - extra
        values = (
            (stage.solution, allowed)
            if sign == 1
            else (stage.solution, a.domains[0], allowed)
        )
        stages = (stage, None) if sign == 1 else (stage, comparison(B, ">"), None)
        solution = sp.Intersection(*values)
        cases.append(BaseCase(sign, op, values, stages, solution))
    if sp.Union(*(c.solution for c in cases)) != a.solution:
        raise UnsupportedCondition(
            "the two plotted base systems must preserve the complete original domain"
        )
    return RationalBaseCases(a, tuple(cases))
