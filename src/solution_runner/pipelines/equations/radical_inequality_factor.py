"""Split zero and strictly positive branches of a nonnegative radical factor."""

import re
from dataclasses import dataclass, replace

import sympy as sp

from ..probability.common import UnsupportedCondition
from .logarithm_rationalization import answer
from .radical_inequality_domains import domain
from .radical_inequality_parser import RadicalParser
from .rational_inequality import OPERATORS, interval_signs, normalize
from .rational_inequality_parser import X, checked, polynomial
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class NonnegativeRootFactor:
    method: str
    numerator: sp.Expr
    denominator: object
    left_coefficient: sp.Expr
    right_coefficient: sp.Expr
    coefficient_node: object
    operator: str
    constraints: object
    zero_candidates: object
    zero_case: object
    positive_domain: object
    stage: object
    positive_case: object
    solution: object

    @property
    def answer(self):
        return answer(self.solution)


def square_quotient(left, right, radicands):
    items = list(radicands.items())
    candidates = [
        (s, p)
        for s, p in items
        if polynomial(p).degree() == 2
        and polynomial(p).LC() == 1
        and sp.discriminant(p, X) == 0
    ]
    if len(candidates) != 1:
        raise UnsupportedCondition(
            "the square numerator must be a complete square of an affine polynomial"
        )
    symbol, numerator = candidates[0]
    other, denominator = next((s, p) for s, p in items if s != symbol)
    if polynomial(denominator).degree() != 1:
        raise UnsupportedCondition(
            "one affine radicand is required in the squared quotient denominator"
        )
    factor = (symbol - 1) ** 2 / (other - 1) ** 2
    L, R = (sp.cancel(n.value / factor) for n in (left, right))
    checked(L)
    checked(R)
    if R.free_symbols:
        raise UnsupportedCondition(
            "the squared-factor parent needs a constant on the right after division"
        )
    return numerator, denominator, L, R, None, numerator - 1


def normalized_stage(coefficient, operator, denominators):
    stage = comparison(coefficient, operator, denominators=denominators)
    expression, sign_operator = normalize(coefficient, operator)
    signs, solution = interval_signs(
        expression, stage.points, sign_operator, stage.poles
    )
    if solution != stage.solution:
        raise UnsupportedCondition(
            "normalizing the rational coefficient must preserve all original exclusions"
        )
    return replace(
        stage, expression=expression, sign_operator=sign_operator, signs=signs
    )


def analyze(formula):
    parts = re.split(r"(\\(?:lt|gt|leq?|geq?)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or OPERATORS.get(parts[1]) not in ("<=", ">="):
        raise UnsupportedCondition(
            "one complete nonstrict radical-product inequality is required"
        )
    radicands, denominators = {}, []
    left, right = (
        RadicalParser(p, denominators, radicands=radicands).parse()
        for p in (parts[0], parts[2])
    )
    if len(radicands) == 2:
        numerator, denominator, L, R, node, zero = square_quotient(
            left, right, radicands
        )
        method = "squared_quotient"
    elif len(radicands) == 1:
        symbol, numerator = next(iter(radicands.items()))
        if (
            right.value != 0
            or left.kind != "multiply"
            or left.children[1].kind != "root"
            or left.children[1].value != symbol
        ):
            raise UnsupportedCondition(
                "the root-factor parent requires a complete rational coefficient times one root"
            )
        p = polynomial(numerator)
        if p.degree() != 2 or p.LC() >= 0 or sp.discriminant(p.as_expr(), X) <= 0:
            raise UnsupportedCondition(
                "the root factor needs a concave quadratic with two distinct real zeros"
            )
        node = left.children[0]
        L = checked(node.value)
        R = sp.Integer(0)
        denominator = None
        zero = numerator
        method = "root_factor"
    else:
        raise UnsupportedCondition(
            "one root factor or a squared quotient of two roots is required"
        )
    coefficient = sp.cancel(L - R)
    if coefficient == 0:
        raise UnsupportedCondition(
            "the reviewed method requires a nonzero rational coefficient"
        )
    constraints = domain(radicands, denominators)
    zero_candidates = comparison(zero, "=").solution
    zero_case = zero_candidates.intersect(constraints.values)
    positive_domain = constraints.values - zero_candidates
    operator = OPERATORS[parts[1]]
    stage = normalized_stage(coefficient, operator, constraints.rational_denominators)
    positive_case = stage.solution.intersect(positive_domain)
    solution = sp.Union(zero_case, positive_case)
    return NonnegativeRootFactor(
        method,
        numerator,
        denominator,
        L,
        R,
        node,
        operator,
        constraints,
        zero_candidates,
        zero_case,
        positive_domain,
        stage,
        positive_case,
        solution,
    )
