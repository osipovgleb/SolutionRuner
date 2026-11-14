"""Certify the parent's two substitutions and quadratic-exponent inverse branches."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms
from .exponential_inequality_preimages import branches as power_branches
from .exponential_inequality_preimages import power_range
from .exponential_inequality_quadratic import normalize_powers
from .exponential_inequality_quadratic_labels import root_text
from .rational_exponential_input import leaves, original_domains, substitute
from .rational_inequality import analyze as rational
from .rational_inequality import set_latex
from .rational_inequality_parser import RationalParser, X, polynomial
from .rational_inequality_proof import RELATION
from .rational_inequality_substitutions import inverse_set
from .rational_substitution_preimages import branches, comparison


@dataclass(frozen=True)
class NestedReciprocal:
    base: sp.Expr
    exponent: sp.Expr
    operator: str
    original_power: sp.Expr
    coefficients: tuple
    stage: object
    inverse_branches: tuple
    y_solution: object
    power_solution: object
    power_range: object
    reachable: object
    branches: tuple
    back: tuple
    solution: object

    def endpoint(self, value):
        return root_text(self, value)

    @property
    def answer(self):
        return set_latex(self.solution, endpoint=self.endpoint)


def converted(formula):
    left, right, denominators, operator = read_terms(formula)
    powers = leaves(left) + leaves(right)
    if not 1 <= len(powers) <= 24:
        raise UnsupportedCondition("one to twenty-four exponential leaves are required")
    base, exponent, _ = normalize_powers(
        [(sp.Integer(1), *(c.value for c in node.children)) for node in powers],
        sp.Integer(0),
        exponent_degree=2,
        preserve_shift=True,
    )
    poles, original_poles = original_domains(denominators, base, exponent)
    if poles != {sp.Integer(1)} or original_poles:
        raise UnsupportedCondition("the reviewed nested domain excludes only power one")
    original = (
        RationalParser(substitute(left, base, exponent)).parse().value
        - RationalParser(substitute(right, base, exponent)).parse().value
    )
    y = sp.cancel(original.subs(X, X + 1))
    t = sp.cancel(y.subs(X, 1 / X))
    p = polynomial(t)
    if p.degree() != 2 or any(
        c.is_Rational is not True or max(abs(c.p), c.q) > 10**12 for c in p.all_coeffs()
    ):
        raise UnsupportedCondition(
            "the reciprocal substitution must yield a bounded rational quadratic"
        )
    return base, exponent, operator, original, p


def y_cases(inverse_branches):
    return tuple(
        part
        for branch in inverse_branches
        for part in (
            branch.solution.args
            if isinstance(branch.solution, sp.Union)
            else (branch.solution,)
        )
        if part != sp.EmptySet
    )


def positive_case(values):
    return inverse_set(values, sp.Integer(1), sp.Integer(-1)).intersect(
        sp.Interval.open(0, sp.oo)
    )


def analyze(formula):
    base, exponent, operator, original, p = converted(formula)
    stage = rational(sp.latex(p.as_expr()) + RELATION[operator] + "0")
    inverse_branches = branches(
        stage.solution,
        sp.S.Reals - sp.FiniteSet(0),
        lambda bound, op: comparison(1 / X - bound, op),
    )
    y_solution = sp.Union(*(b.solution for b in inverse_branches))
    positive = positive_case(y_solution)
    value_range = power_range(base, exponent)
    reachable = positive.intersect(value_range)
    parts = tuple(
        branch
        for values in y_cases(inverse_branches)
        for branch in power_branches(
            base, exponent, positive_case(values).intersect(value_range)
        )
    )
    back = tuple((c.bound, c.value, c.points) for b in parts for c in b.conditions)
    solution = sp.Union(*(b.solution for b in parts))
    return NestedReciprocal(
        base,
        exponent,
        operator,
        original,
        tuple(p.all_coeffs()),
        stage,
        tuple(inverse_branches),
        y_solution,
        positive,
        value_range,
        reachable,
        parts,
        back,
        solution,
    )
