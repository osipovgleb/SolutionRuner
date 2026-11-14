"""Keep exponential substitution positive and square only a nonnegative right side."""

import re
from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exam_exponential_proof import labels
from .exponential_inequality_parser import ExponentialParser
from .exponential_inequality_quadratic import inverse, normalize_powers
from .power_arithmetic import balanced
from .rational_exponential_input import leaves, substitute
from .rational_inequality import set_latex
from .rational_inequality_parser import RationalParser, X, polynomial
from .rational_substitution_preimages import comparison


@dataclass(frozen=True)
class ExponentialRoot:
    base: sp.Expr
    exponent: sp.Expr
    radicand: sp.Expr
    right: sp.Expr
    domain_stage: object
    square_stage: object
    domain: object
    negative_case: object
    nonnegative_case: object
    positive_solution: object
    solution: object
    back: tuple

    def endpoint(self, value):
        return labels(self, number_formatter=sp.latex, preserve_offset=True).get(
            value, sp.latex(value)
        )

    @property
    def answer(self):
        return set_latex(self.solution, endpoint=self.endpoint)


def read(formula):
    parts = re.split(r"(\\(?:geq?|leq?|gt|lt)(?![a-zA-Z])|<|>)", formula)
    if len(parts) != 3 or parts[1] not in (r"\ge", r"\geq"):
        raise UnsupportedCondition(
            "one complete nonnegative square-root comparison is required"
        )
    left = parts[0].strip()
    if not left.startswith(r"\sqrt{"):
        raise UnsupportedCondition("the complete left side must be one square root")
    raw, end = balanced(left, 5)
    if end != len(left):
        raise UnsupportedCondition(
            "no term outside the complete left square root is supported"
        )
    denominators = []
    nodes = tuple(ExponentialParser(p, denominators).parse() for p in (raw, parts[2]))
    if any(d.free_symbols for d in denominators):
        raise UnsupportedCondition(
            "the polynomial exponential parent has no variable denominators"
        )
    powers = tuple(
        (sp.Integer(1), *(c.value for c in p.children))
        for n in nodes
        for p in leaves(n)
    )
    if not powers:
        raise UnsupportedCondition("a genuine exponential substitution is required")
    base, exponent, _ = normalize_powers(powers, sp.Integer(0))
    values = tuple(
        RationalParser(substitute(n, base, exponent)).parse().value for n in nodes
    )
    return base, exponent, values


def analyze(formula):
    base, exponent, (Q, R) = read(formula)
    q, r = polynomial(Q), polynomial(R)
    domain_stage = comparison(Q, ">=")
    if (
        q.degree() != 2
        or q.LC() <= 0
        or r.degree() != 1
        or r.LC() <= 0
        or len(domain_stage.zeros) != 2
        or any(p.is_positive is not True for p in domain_stage.zeros)
        or sp.simplify(R.subs(X, domain_stage.zeros[-1])) != 0
    ):
        raise UnsupportedCondition(
            "a positive quadratic with two positive zeros and an increasing right side vanishing at its upper zero is required"
        )
    domain = domain_stage.solution.intersect(sp.Interval.open(0, sp.oo))
    negative = domain.intersect(comparison(R, "<").solution)
    nonnegative = domain.intersect(comparison(R, ">=").solution)
    square_stage = comparison(Q - R**2, ">=")
    positive = negative.union(nonnegative.intersect(square_stage.solution))
    points = set(domain_stage.zeros) | set(square_stage.zeros)
    points = tuple(p for p in points if p.is_positive is True)
    _, back = back_substitute(base, exponent, points)
    mapping = {t: branches[0] for t, _, branches in back}
    solution = inverse(positive, mapping, polynomial(exponent).LC() > 0)
    return ExponentialRoot(
        base,
        exponent,
        Q,
        R,
        domain_stage,
        square_stage,
        domain,
        negative,
        nonnegative,
        positive,
        solution,
        tuple(back),
    )
