"""Certify a nonnegative squared logarithm factor and its exact zero branch."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .logarithm_factor_arguments import read_argument
from .logarithm_rationalization import answer
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison


def read_product(formula):
    parts = re.split(
        r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula.removesuffix(".")
    )
    if len(parts) != 3 or parts[1] not in (r"\le", r"\leq"):
        raise UnsupportedCondition(
            "one complete nonstrict square-factor inequality is required"
        )
    arguments = []

    def reader(raw):
        argument = read_argument(raw)
        arguments.append(argument)
        return argument.value

    atoms, expression = read_equation(
        parts[0] + "=" + parts[2],
        extended=True,
        argument_reader=reader,
        argument_powers=True,
    )
    if len(atoms) != 3 or any(a.root or a.denominator for a in atoms):
        raise UnsupportedCondition(
            "three complete polynomial-argument logarithms are required"
        )
    return tuple(atoms), tuple(arguments), expression


@dataclass(frozen=True)
class SquareLogFactor:
    base: sp.Expr
    A: sp.Expr
    B: sp.Expr
    atoms: tuple
    arguments: tuple
    domain: object
    stage: object
    zero_case: object
    log_case: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    atoms, arguments, expression = read_product(formula)
    first, square, last = atoms
    base = last.base
    A, B = first.argument, last.argument
    if (
        base.is_Rational is not True
        or not 1 < base <= 1000
        or first.base not in (base, 1 / base)
        or square.base != base
        or not A.is_polynomial(X)
        or not B.is_polynomial(X)
        or polynomial(A).degree() != 1
        or polynomial(B).degree() != 1
        or sp.expand(square.argument - A**2) != 0
    ):
        raise UnsupportedCondition(
            "same or reciprocal increasing-reference bases, two affine arguments and their exact square are required"
        )
    u, v = sp.symbols("L M", real=True)
    converted = sp.expand(
        expression.subs(
            {
                first.symbol: u if first.base == base else -u,
                square.symbol: 2 * u,
                last.symbol: v,
            },
            simultaneous=True,
        )
    )
    if sp.expand(converted - (u - 1) ** 2 * v) != 0:
        raise UnsupportedCondition(
            "the whole original expression must equal a nonnegative square times the second logarithm"
        )
    domain = sp.Intersection(*(arg.domain for arg in arguments))
    stage = comparison((A - base) ** 2 * (B - 1), "<=")
    zero_case = comparison(A - base, "=").solution.intersect(domain)
    log_case = comparison(B - 1, "<=").solution.intersect(domain)
    solution = stage.solution.intersect(domain)
    if sp.Union(zero_case, log_case) != solution:
        raise UnsupportedCondition(
            "the zero branch and nonpositive logarithm branch must exhaust the complete original domain"
        )
    return SquareLogFactor(
        base, A, B, atoms, arguments, domain, stage, zero_case, log_case, solution
    )
