"""Project a squared affine root only on its complete original real domain."""

import re
from dataclasses import dataclass, replace

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_rationalization import answer
from .radical_inequality_domains import domain
from .radical_inequality_factor import normalized_stage
from .radical_inequality_parser import RadicalParser
from .rational_inequality import OPERATORS
from .rational_inequality_parser import X, checked, polynomial
from .rational_inequality_polynomial_methods import collect


def without_square(node, symbol):
    return replace(
        node,
        value=node.value.subs(symbol**2, 0),
        children=tuple(without_square(c, symbol) for c in node.children),
    )


def one_fraction(node, *, degree):
    whole, values = collect(node)
    if len(values) != 1 or polynomial(whole).degree() > degree:
        raise UnsupportedCondition(
            "one reviewed fraction and a bounded polynomial part are required"
        )
    numerator, denominator = values[0]
    if polynomial(numerator).degree() > 0 or polynomial(denominator).degree() != 1:
        raise UnsupportedCondition(
            "a constant numerator and an affine original denominator are required"
        )
    return whole, numerator, denominator


@dataclass(frozen=True)
class EvenRootPower:
    radicand: sp.Expr
    first: tuple
    second: tuple
    first_numerator: sp.Expr
    second_numerator: sp.Expr
    cancelled_first: sp.Expr
    constraints: object
    stage: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def analyze(formula):
    parts = re.split(r"(\\(?:lt|gt|leq?|geq?)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or OPERATORS.get(parts[1]) != ">=":
        raise UnsupportedCondition(
            "the even-root-power parent requires one complete nonnegative product"
        )
    radicands, denominators = {}, []
    left, right = (
        RadicalParser(p, denominators, radicands=radicands).parse()
        for p in (parts[0], parts[2])
    )
    if right.value != 0 or left.kind != "multiply" or len(radicands) != 1:
        raise UnsupportedCondition(
            "two complete factors and one affine root squared are required"
        )
    symbol, radicand = next(iter(radicands.items()))
    if polynomial(radicand).degree() != 1 or any(
        d.free_symbols & radicands.keys() for d in denominators
    ):
        raise UnsupportedCondition(
            "one affine radicand and original rational denominators are required"
        )
    first_node, second_node = left.children
    checked(first_node.value)
    if not second_node.value.is_polynomial(symbol):
        raise UnsupportedCondition(
            "the second factor must be polynomial in the root symbol"
        )
    root_poly = sp.Poly(second_node.value, symbol)
    if root_poly.degree() != 2 or root_poly.nth(2) != 1 or root_poly.nth(1) != 0:
        raise UnsupportedCondition(
            "the entire second factor must contain one unit square and no odd root powers"
        )
    first = one_fraction(first_node, degree=1)
    second = one_fraction(without_square(second_node, symbol), degree=0)
    w, n, d = first
    v, m, e = second
    first_numerator = sp.expand(w * d + n)
    second_numerator = sp.expand(m + v * e + radicand * e)
    cancelled_first = sp.cancel(first_numerator / e)
    if (
        not cancelled_first.is_polynomial(X)
        or polynomial(cancelled_first).degree() != 1
        or polynomial(second_numerator).degree() != 2
    ):
        raise UnsupportedCondition(
            "the reviewed affine denominator must cancel from a quadratic first numerator"
        )
    projected = checked(first_numerator * second_numerator / (d * e))
    if sp.cancel(projected - left.value.subs(symbol**2, radicand)) != 0:
        raise UnsupportedCondition(
            "the projection must equal the entire original expression on its domain"
        )
    constraints = domain(radicands, denominators)
    stage = normalized_stage(projected, ">=", constraints.rational_denominators)
    solution = stage.solution.intersect(constraints.values)
    return EvenRootPower(
        radicand,
        first,
        second,
        first_numerator,
        second_numerator,
        cancelled_first,
        constraints,
        stage,
        solution,
    )
