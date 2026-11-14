"""Reuse exact rational comparisons for absolute bounds and retain source poles."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_inequality_input import AbsoluteParser
from .exponential_inequality_common_base import read_terms
from .rational_inequality import set_latex
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison, excluded_points

METHODS = ("squared_quotient", "affine_substitution", "quadratic_comparison")


def absolute_comparison(argument, operator, bound):
    stages = (
        comparison(argument - bound, operator),
        comparison(-argument - bound, operator),
    )
    values = (s.solution for s in stages)
    return stages, sp.Union(*values) if operator in (">", ">=") else sp.Intersection(
        *values
    )


@dataclass(frozen=True)
class AbsoluteInequality:
    method: str
    argument: sp.Expr
    bound: sp.Expr
    denominator: sp.Expr
    inverse_factors: tuple
    branches: tuple
    substitution_stage: object
    poles: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def read(formula):
    values = {}
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: AbsoluteParser(text, values=values)
    )
    if len(values) != 1:
        raise UnsupportedCondition("one complete polynomial modulus is required")
    symbol, argument = next(iter(values.items()))
    return left, right, operator, symbol, argument, excluded_points(denominators)


def squared_quotient(left, right, operator, symbol, argument, poles):
    if (
        operator != "<="
        or left.kind != "power"
        or left.children[1].value != 2
        or right.kind != "divide"
        or right.children[0].kind != "absolute"
    ):
        raise UnsupportedCondition(
            "a squared inverse difference compared with one modulus over a squared denominator is required"
        )
    difference = left.children[0]
    denominator = right.children[1]
    if (
        difference.kind != "subtract"
        or denominator.kind != "power"
        or denominator.children[1].value != 2
    ):
        raise UnsupportedCondition(
            "the entire inverse difference and denominator square must match the parent"
        )
    factors = []
    for node in difference.children:
        if (
            node.kind != "power"
            or node.children[1].value != -1
            or polynomial(node.children[0].value).degree() != 1
        ):
            raise UnsupportedCondition(
                "both source terms must be reciprocals of affine polynomials"
            )
        factors.append(node.children[0].value)
    D = denominator.children[0].value
    if (
        polynomial(D).degree() != 2
        or sp.cancel(D - factors[0] * factors[1]) != 0
        or polynomial(argument).degree() != 2
    ):
        raise UnsupportedCondition(
            "the complete source denominator must be the product of the affine factors"
        )
    K = sp.cancel(left.value * D**2)
    if (
        K.is_Rational is not True
        or K <= 0
        or sp.cancel(right.value - symbol / D**2) != 0
    ):
        raise UnsupportedCondition(
            "the whole squared numerator must reduce to a positive rational constant"
        )
    polynomial(K)
    branches, solution = absolute_comparison(argument, ">=", K)
    return AbsoluteInequality(
        "squared_quotient",
        argument,
        K,
        D,
        tuple(factors),
        branches,
        None,
        poles,
        solution - sp.FiniteSet(*poles),
    )


def affine_substitution(left, right, operator, symbol, argument, poles):
    if operator != "<" or polynomial(argument).degree() != 1:
        raise UnsupportedCondition(
            "the parent uses a strict quadratic inequality in an affine modulus"
        )
    expression = sp.expand(left.value - right.value)
    q = sp.Poly(expression, symbol)
    if (
        q.degree() != 1
        or q.nth(1).is_Rational is not True
        or q.nth(1) >= 0
        or sp.expand(q.nth(0) - argument**2) != 0
    ):
        raise UnsupportedCondition(
            "the entire polynomial part must equal the square of the modulus argument"
        )
    K = -q.nth(1)
    stage = comparison(X**2 - K * X, "<")
    lower, lo = absolute_comparison(argument, ">", 0)
    upper, hi = absolute_comparison(argument, "<", K)
    return AbsoluteInequality(
        "affine_substitution",
        argument,
        K,
        sp.Integer(1),
        (),
        lower + upper,
        stage,
        poles,
        lo.intersect(hi) - sp.FiniteSet(*poles),
    )


def analyze(formula, method):
    if method not in METHODS:
        raise UnsupportedCondition(
            "a reviewed absolute-inequality parent method is required"
        )
    args = read(formula)
    return {
        "squared_quotient": squared_quotient,
        "affine_substitution": affine_substitution,
        "quadratic_comparison": quadratic_comparison,
    }[method](*args)


def quadratic_comparison(left, right, operator, symbol, argument, poles):
    if (
        operator != ">="
        or left.kind != "absolute"
        or left.value != symbol
        or polynomial(argument).degree() != 2
        or right.value.has(symbol)
        or polynomial(right.value).degree() != 2
        or poles
    ):
        raise UnsupportedCondition(
            "the parent compares one whole quadratic modulus with a quadratic without source poles"
        )
    _, solution = absolute_comparison(argument, operator, right.value)
    branches = []
    for value in (right.value - argument, right.value + argument):
        q = polynomial(value)
        if q.degree() != 2 or q.LC() <= 0:
            raise UnsupportedCondition(
                "both parent branches must be upward quadratic comparisons"
            )
        stage = comparison(q.monic().as_expr(), "<=")
        if not isinstance(stage.solution, sp.Interval) or len(stage.points) != 2:
            raise UnsupportedCondition(
                "the reviewed chart needs two distinct roots in each quadratic branch"
            )
        branches.append(stage)
    return AbsoluteInequality(
        "quadratic_comparison",
        argument,
        right.value,
        sp.Integer(1),
        (),
        tuple(branches),
        None,
        poles,
        solution,
    )
