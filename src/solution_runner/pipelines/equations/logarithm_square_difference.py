"""Factor squared logarithms into two exact sign systems on the original domain."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_logarithmic_input import read_equation
from .logarithm_arithmetic import log_ratio
from .logarithm_factor_arguments import read_argument
from .rational_inequality import OPERATORS, set_latex
from .rational_inequality_factor_methods import positive_quadratics
from .rational_inequality_parser import X
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class SignSystem:
    sum_stage: object
    difference_stage: object
    solution: object


@dataclass(frozen=True)
class SquareDifference:
    base: sp.Expr
    atoms: tuple
    arguments: tuple
    operator: str
    domain: object
    coarse_domain: object
    hole: sp.Expr
    ratio_root: sp.Expr
    product_root: sp.Expr
    positive_factors: tuple
    systems: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def read_input(formula):
    formula = re.sub(r"\\lg(?![a-zA-Z])", lambda _: r"\log_{10}", formula)
    parts = re.split(r"(\\(?:gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in OPERATORS:
        raise UnsupportedCondition(
            "one strict difference of logarithm squares is required"
        )
    arguments = []

    def reader(text):
        arg = read_argument(text)
        arguments.append(arg)
        return arg.value

    atoms, expression = read_equation(
        parts[0] + "=" + parts[2], extended=True, argument_reader=reader
    )
    if len(atoms) != 2 or any(a.root or a.denominator for a in atoms):
        raise UnsupportedCondition("two complete logarithm squares are required")
    if expression != atoms[0].symbol ** 2 - atoms[1].symbol ** 2:
        raise UnsupportedCondition(
            "the whole comparison must be a difference of squares"
        )
    base = atoms[0].base
    if base.is_Rational is not True or base <= 1 or max(base.p, base.q) > 1000:
        raise UnsupportedCondition(
            "one bounded increasing rational reference base is required"
        )
    if log_ratio(base, atoms[1].base) not in (1, -1):
        raise UnsupportedCondition(
            "the squared logarithm bases must coincide or be reciprocal"
        )
    return base, tuple(atoms), tuple(arguments), OPERATORS[parts[1]]


def shape(arguments):
    first, second = arguments
    if any(not arg.value.is_polynomial(X) for arg in arguments):
        raise UnsupportedCondition("two original polynomial arguments are required")
    if sp.degree(first.value, X) != 3 or sp.degree(second.value, X) != 1:
        raise UnsupportedCondition(
            "a cubic and an affine polynomial argument are required"
        )
    if any(
        arg.denominator != 1 and sp.degree(arg.denominator, X) != 0 for arg in arguments
    ):
        raise UnsupportedCondition("the reviewed argument denominators are constant")
    factors = first.factors
    squares = [
        factor
        for factor, degree in factors
        if degree == 2 and sp.degree(factor, X) == 1
    ]
    if len(squares) != 1 or any(arg.coefficient <= 0 for arg in arguments):
        raise UnsupportedCondition(
            "a single common affine square and positive coefficients are required"
        )
    factor = squares[0]
    affine = sp.cancel(second.value / second.coefficient)
    if sp.cancel(first.value - first.coefficient * factor**2 * affine) != 0:
        raise UnsupportedCondition("both arguments must share the same affine factor")
    ratio_root = sp.sqrt(first.coefficient / second.coefficient) * factor
    product_root = sp.sqrt(first.coefficient * second.coefficient) * factor * affine
    if any(
        c.is_Rational is not True
        for p in (ratio_root, product_root)
        for c in sp.Poly(p, X).all_coeffs()
    ):
        raise UnsupportedCondition(
            "the two square roots need rational polynomial coefficients"
        )
    hole = sp.solve(factor, X)[0]
    coarse = comparison(affine, ">").solution
    domain = sp.Intersection(*(arg.domain for arg in arguments))
    if coarse - sp.FiniteSet(hole) != domain:
        raise UnsupportedCondition(
            "all original exclusions must be retained in the displayed domain"
        )
    return domain, coarse, hole, ratio_root, product_root


def analyze(formula):
    base, atoms, arguments, operator = read_input(formula)
    domain, coarse, hole, ratio_root, product_root = shape(arguments)
    full_sum = comparison(product_root**2 - 1, ">")
    positive = tuple(positive_quadratics(full_sum))
    reduced = sp.cancel(full_sum.original / sp.prod(f for f, _ in positive))
    if (
        sp.degree(reduced, X) != 2
        or comparison(reduced, ">").solution != full_sum.solution
    ):
        raise UnsupportedCondition(
            "removing positive quadratic factors must preserve the sum sign"
        )
    signs = (("<", ">"), (">", "<")) if operator == "<" else (("<", "<"), (">", ">"))
    systems = []
    for sum_op, difference_op in signs:
        sum_stage = comparison(reduced, sum_op)
        difference_stage = comparison(ratio_root**2 - 1, difference_op)
        solution = sp.Intersection(
            domain, sum_stage.solution, difference_stage.solution
        )
        systems.append(SignSystem(sum_stage, difference_stage, solution))
    return SquareDifference(
        base,
        atoms,
        arguments,
        operator,
        domain,
        coarse,
        hole,
        ratio_root,
        product_root,
        positive,
        tuple(systems),
        sp.Union(*(s.solution for s in systems)),
    )
