"""Compare three same-base logarithms while certifying the original argument domain."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .rational_inequality import OPERATORS, set_latex
from .rational_inequality_parser import polynomial
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class ProductComparison:
    formula: str
    operator: str
    base: sp.Expr
    arguments: tuple
    domains: tuple
    displayed_indices: tuple
    domain: object
    display_domain: object
    stage: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def analyze(formula):
    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition("one complete logarithmic inequality is required")
    atoms, expression = read_equation(parts[0] + "=" + parts[2], extended=True)
    if len(atoms) != 3 or any(a.root or a.denominator for a in atoms):
        raise UnsupportedCondition(
            "three complete logarithms without outer roots or poles are required"
        )
    base = atoms[0].base
    if (
        base.is_Rational is not True
        or base <= 0
        or base == 1
        or any(a.base != base for a in atoms)
    ):
        raise UnsupportedCondition(
            "the three logarithms must have the same positive rational base different from one"
        )
    if sp.expand(expression - atoms[0].symbol + atoms[1].symbol + atoms[2].symbol) != 0:
        raise UnsupportedCondition(
            "one logarithm must be compared with the sum of two others"
        )
    arguments = tuple(a.argument for a in atoms)
    if any(polynomial(value).degree() not in (1, 2) for value in arguments):
        raise UnsupportedCondition("the reviewed arguments must be affine or quadratic")
    operator = OPERATORS[parts[1]]
    A, B, C = arguments
    difference = sp.expand((1 if base > 1 else -1) * (A - B * C))
    if polynomial(difference).degree() != 3:
        raise UnsupportedCondition(
            "the parent grouping requires a cubic argument difference"
        )
    stage = comparison(difference, operator)
    domains = tuple(comparison(argument, ">") for argument in arguments)
    domain = sp.Intersection(*(d.solution for d in domains))
    implied = (base < 1 and operator in ("<", "<=")) or (
        base > 1 and operator in (">", ">=")
    )
    indices = (1, 2) if implied else (0, 1, 2)
    display_domain = sp.Intersection(*(domains[i].solution for i in indices))
    solution = stage.solution.intersect(domain)
    if display_domain.intersect(stage.solution) != solution:
        raise UnsupportedCondition(
            "the displayed domain conditions must imply every omitted argument restriction"
        )
    return ProductComparison(
        formula,
        operator,
        base,
        arguments,
        domains,
        indices,
        domain,
        display_domain,
        stage,
        solution,
    )
