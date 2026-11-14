"""Keep both base-sign cases and the original domains of one polynomial logarithm."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_inequality import rational_polynomial
from .exponential_inequality_common_base import read_terms
from .exponential_root_quotient import analyze as root_quotient
from .logarithm_exponential_input import ExponentialLogParser
from .rational_inequality import FLIPPED, set_latex
from .rational_substitution_preimages import comparison, excluded_points
from .variable_logarithm_parser import Atoms


@dataclass(frozen=True)
class PolynomialLogCases:
    base: sp.Expr
    argument: sp.Expr
    operator: str
    domain: object
    poles: tuple
    cases: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def logarithm_cases(formula):
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: ExponentialLogParser(text, atoms=atoms)
    )
    if (
        len(atoms.values) != 1
        or left.kind != "logarithm"
        or right.kind != "scalar"
        or right.value != 0
        or left.value != atoms.values[0].symbol
    ):
        raise UnsupportedCondition(
            "one whole polynomial-base logarithm compared with zero is required"
        )
    (atom,) = atoms.values
    B, Q = map(sp.cancel, (atom.base, atom.argument))
    base = rational_polynomial(B, 2)
    argument = rational_polynomial(Q, 2)
    if base.LC() <= 0 or sp.discriminant(base) != 0 or argument.LC() <= 0:
        raise UnsupportedCondition(
            "the parent needs a positive affine square base and an upward quadratic argument"
        )
    poles = excluded_points((*denominators, B - 1))
    base_domain = comparison(B, ">", denominators=denominators).solution - sp.FiniteSet(
        *poles
    )
    argument_domain = comparison(Q, ">").solution
    domain = base_domain.intersect(argument_domain)
    cases = []
    for sign, op in ((-1, "<"), (1, ">")):
        values = base_domain.intersect(comparison(B - 1, op).solution)
        argument_operator = FLIPPED[operator] if sign == -1 else operator
        stage = comparison(Q - 1, argument_operator)
        allowed = stage.solution.intersect(argument_domain)
        cases.append(
            (sign, argument_operator, values, allowed, values.intersect(allowed))
        )
    return PolynomialLogCases(
        B, Q, operator, domain, poles, tuple(cases), sp.Union(*(s[-1] for s in cases))
    )


def analyze(formula):
    return logarithm_cases(formula) if r"\log_" in formula else root_quotient(formula)
