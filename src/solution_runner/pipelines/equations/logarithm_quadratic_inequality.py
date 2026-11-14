"""Invert a quadratic in one constant-base logarithm using exact shared branches."""

import re
from dataclasses import dataclass
from functools import partial

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .rational_inequality import FLIPPED, OPERATORS, set_latex
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import branches, comparison


@dataclass(frozen=True)
class QuadraticLogarithm:
    base: sp.Expr
    argument: sp.Expr
    operator: str
    stage: object
    domain: object
    branches: tuple
    solution: object
    reciprocal_base: bool = False

    @property
    def answer(self):
        return set_latex(self.solution)


def inverse(base, argument, level, operator):
    if level.is_Integer is not True or abs(level) > 8:
        raise UnsupportedCondition(
            "the reviewed logarithm levels are integers within eight"
        )
    if base < 1 and operator != "=":
        operator = FLIPPED[operator]
    return comparison(argument - base**level, operator)


def analyze(formula):
    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition(
            "one complete quadratic logarithm inequality is required"
        )
    atoms, value = read_equation(parts[0] + "=" + parts[2], extended=True)
    if not atoms:
        raise UnsupportedCondition("one complete logarithm is required")
    if value.free_symbols - {a.symbol for a in atoms}:
        raise UnsupportedCondition("the outer expression may depend only on logarithms")
    base, argument = atoms[0].base, atoms[0].argument
    if base.is_Rational is not True or polynomial(argument).degree() not in (1, 2):
        raise UnsupportedCondition(
            "one constant rational base and polynomial argument are required"
        )
    substitutions = {}
    for atom in atoms:
        if atom.argument != argument or atom.root or atom.denominator:
            raise UnsupportedCondition(
                "the complete polynomial logarithm argument must coincide"
            )
        if atom.base not in (base, 1 / base):
            raise UnsupportedCondition(
                "only the same or reciprocal logarithm base is reviewed"
            )
        substitutions[atom.symbol] = X if atom.base == base else -X
    value = sp.expand(value.subs(substitutions, simultaneous=True))
    if polynomial(value).degree() != 2:
        raise UnsupportedCondition(
            "the outer expression must be a quadratic of the logarithm"
        )
    operator = OPERATORS[parts[1]]
    stage = comparison(value, operator)
    if len(stage.zeros) != 2 or any(
        r.is_Integer is not True or abs(r) > 8 for r in stage.zeros
    ):
        raise UnsupportedCondition(
            "two distinct bounded integer logarithm roots are required"
        )
    domain = comparison(argument, ">").solution
    parts = branches(stage.solution, domain, partial(inverse, base, argument))
    return QuadraticLogarithm(
        base,
        argument,
        operator,
        stage,
        domain,
        parts,
        sp.Union(*(part.solution for part in parts)),
        any(atom.base != base for atom in atoms),
    )
