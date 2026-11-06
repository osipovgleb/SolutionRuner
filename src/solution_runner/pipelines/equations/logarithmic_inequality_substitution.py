"""A quadratic in two same-base logarithms with an exact argument quotient."""

from dataclasses import dataclass
from functools import partial

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms
from .rational_inequality import FLIPPED, set_latex
from .rational_inequality_parser import X, polynomial
from .rational_inequality_roots import real_roots
from .rational_substitution_preimages import branches, comparison, excluded_points
from .variable_logarithm_parser import Atoms, VariableLogarithmParser


@dataclass(frozen=True)
class LogarithmicSubstitution:
    formula: str
    operator: str
    atoms: tuple
    shift: int
    stage: object
    poles: tuple
    domain: object
    increasing_domain: object
    decreasing_domain: object
    branches: tuple
    solution: object

    @property
    def base(self):
        return self.atoms[0].base

    @property
    def argument(self):
        return self.atoms[0].argument

    @property
    def answer(self):
        return set_latex(self.solution)


def inverse(atom, level, operator, *, increasing):
    if level.is_Integer is not True or abs(level) > 4:
        raise UnsupportedCondition("this log inverse needs small integer levels")
    if not increasing and operator != "=":
        operator = FLIPPED[operator]
    return comparison(atom.argument - atom.base**level, operator)


def analyze(formula):
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: VariableLogarithmParser(text, atoms=atoms)
    )
    if len(atoms.values) != 2:
        raise UnsupportedCondition(
            "two logarithms with a common variable base are required"
        )
    first, second = atoms.values
    if sp.cancel(first.base - second.base) != 0 or not first.base.free_symbols:
        raise UnsupportedCondition("the two complete variable bases must coincide")
    for value in (first.base, first.argument):
        if polynomial(value).degree() not in (1, 2):
            raise UnsupportedCondition(
                "quadratic or affine base and first argument are required"
            )
    shifts = [
        k
        for k in range(1, 7)
        if sp.cancel(second.argument - first.argument / first.base**k) == 0
    ]
    if len(shifts) != 1:
        raise UnsupportedCondition(
            "the second argument must divide the first by a base power"
        )
    value = sp.cancel(
        (left.value - right.value).subs(second.symbol, first.symbol - shifts[0])
    )
    if value.free_symbols - {first.symbol}:
        raise UnsupportedCondition(
            "the outer expression must be a polynomial of the substitution"
        )
    value = value.subs(first.symbol, X)
    if polynomial(value).degree() != 2:
        raise UnsupportedCondition("the log substitution must give a quadratic")
    stage = comparison(value, operator)
    poles = excluded_points(denominators)
    domain = sp.S.Reals - sp.FiniteSet(*poles, *real_roots(first.base - 1))
    for original in (first.base, first.argument, second.argument):
        domain = domain.intersect(comparison(original, ">").solution)
    increasing = domain.intersect(comparison(first.base - 1, ">").solution)
    decreasing = domain.intersect(comparison(first.base - 1, "<").solution)
    parts = tuple(
        branch
        for region, grows in ((increasing, True), (decreasing, False))
        for branch in branches(
            stage.solution,
            region,
            partial(inverse, first, increasing=grows),
        )
    )
    return LogarithmicSubstitution(
        formula,
        operator,
        tuple(atoms.values),
        shifts[0],
        stage,
        poles,
        domain,
        increasing,
        decreasing,
        parts,
        sp.Union(*(b.solution for b in parts)),
    )
