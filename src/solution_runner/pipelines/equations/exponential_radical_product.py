"""Solve a root product on its original real domain before selecting its signs."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exam_exponential_proof import labels
from .exponential_inequality_common_base import read_terms
from .exponential_inequality_quadratic import inverse
from .exponential_radical_input import ExponentialRootParser, coordinate, project
from .rational_inequality import set_latex
from .rational_inequality_parser import polynomial
from .rational_inequality_roots import ordered
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class RootProduct:
    base: sp.Expr
    exponent: sp.Expr
    radicand: sp.Expr
    coefficient: sp.Expr
    domain_stage: object
    coefficient_stage: object
    positive_domain: object
    positive_solution: object
    domain: object
    coefficient_zero: sp.Expr
    points: tuple
    signs: tuple
    solution: object
    back: tuple

    def endpoint(self, value):
        return labels(self, number_formatter=sp.latex, preserve_offset=True).get(
            value, sp.latex(value)
        )

    @property
    def answer(self):
        return set_latex(self.solution, endpoint=self.endpoint)


def analyze(formula):
    left, right, denominators, operator = read_terms(
        formula, reader=ExponentialRootParser
    )
    if (
        operator != ">="
        or right.kind != "scalar"
        or right.value != 0
        or left.kind != "multiply"
        or any(d.free_symbols for d in denominators)
    ):
        raise UnsupportedCondition(
            "one complete nonnegative exponential root product without variable denominators is required"
        )
    roots = [n for n in left.children if n.kind == "root"]
    if len(roots) != 1:
        raise UnsupportedCondition("one complete square-root factor is required")
    root = roots[0]
    coefficient = next(n for n in left.children if n is not root)
    base, exponent = coordinate(left)
    Q, C = (project(n, base, exponent) for n in (root.children[0], coefficient))
    q, c = polynomial(Q), polynomial(C)
    domain_stage, coefficient_stage = comparison(Q, ">="), comparison(C, ">=")
    if (
        q.degree() != 2
        or q.LC() <= 0
        or c.degree() != 1
        or c.LC() <= 0
        or len(domain_stage.zeros) != 2
        or any(p.is_positive is not True for p in domain_stage.zeros)
    ):
        raise UnsupportedCondition(
            "an upward quadratic with two positive zeros and an increasing affine coefficient are required"
        )
    threshold = -c.nth(0) / c.nth(1)
    if not domain_stage.zeros[0] < threshold < domain_stage.zeros[1]:
        raise UnsupportedCondition(
            "the coefficient zero must lie inside the forbidden root-domain gap"
        )
    positive_domain = domain_stage.solution.intersect(sp.Interval.open(0, sp.oo))
    positive_solution = positive_domain.intersect(
        coefficient_stage.solution.union(sp.FiniteSet(*domain_stage.zeros))
    )
    _, back = back_substitute(base, exponent, (*domain_stage.zeros, threshold))
    mapping = {t: branches[0] for t, _, branches in back}
    increasing = polynomial(exponent).LC() > 0
    domain = inverse(positive_domain, mapping, increasing)
    solution = inverse(positive_solution, mapping, increasing)
    points = ordered(mapping[t] for t in domain_stage.zeros)
    return RootProduct(
        base,
        exponent,
        Q,
        C,
        domain_stage,
        coefficient_stage,
        positive_domain,
        positive_solution,
        domain,
        mapping[threshold],
        points,
        (-1, 1) if increasing else (1, -1),
        solution,
        tuple(back),
    )
