"""Combine same-base logarithms while retaining the exponential argument domain."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exam_exponential_proof import labels
from .exponential_inequality_common_base import read_terms, vector
from .exponential_inequality_quadratic import inverse
from .logarithm_exponential_input import ExponentialLogParser
from .rational_inequality import set_latex
from .rational_inequality_parser import X, polynomial
from .rational_substitution_preimages import comparison
from .variable_logarithm_parser import Atoms


def affine(value):
    p = polynomial(value)
    if p.degree() > 1 or any(
        c.is_Rational is not True or abs(c) > 40 or c.q > 20 for c in p.all_coeffs()
    ):
        raise UnsupportedCondition(
            "bounded rational affine outer coefficients and exponents are required"
        )
    return p


@dataclass(frozen=True)
class LogarithmExponential:
    logarithm_base: sp.Expr
    constant_argument: sp.Expr
    coefficient: sp.Expr
    right: sp.Expr
    base: sp.Expr
    exponent: sp.Expr
    shift: sp.Expr
    bound: sp.Expr
    stage: object
    positive_domain: object
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
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: ExponentialLogParser(text, atoms=atoms)
    )
    if (
        operator != "<="
        or len(atoms.values) != 2
        or left.kind != "add"
        or any(d.free_symbols for d in denominators)
    ):
        raise UnsupportedCondition(
            "one complete two-logarithm inequality without variable denominators is required"
        )
    weighted, second = left.children
    if weighted.kind != "multiply" or second.kind != "logarithm":
        raise UnsupportedCondition(
            "an affine multiple of a constant logarithm followed by one complete logarithm is required"
        )
    log_nodes = [n for n in weighted.children if n.kind == "logarithm"]
    if len(log_nodes) != 1:
        raise UnsupportedCondition("one complete weighted logarithm is required")
    first = log_nodes[0]
    coefficient = next(n for n in weighted.children if n is not first)
    B, M = (n.value for n in first.children)
    if (
        second.children[0].value != B
        or B.is_Rational is not True
        or B <= 1
        or M.is_Rational is not True
        or M <= 0
    ):
        raise UnsupportedCondition(
            "equal rational increasing logarithm bases and a positive constant argument are required"
        )
    vector(B)
    vector(M)
    argument = second.children[1]
    if (
        argument.kind != "subtract"
        or argument.children[0].kind != "exponential"
        or argument.children[1].value.is_Rational is not True
        or argument.children[1].value <= 0
    ):
        raise UnsupportedCondition(
            "the second complete argument must be one exponential minus a positive rational"
        )
    C, g = (n.value for n in argument.children[0].children)
    d = argument.children[1].value
    if C <= 1 or argument.children[1].value.free_symbols:
        raise UnsupportedCondition(
            "an increasing rational exponential base is required"
        )
    return B, M, coefficient.value, right.value, C, g, d


def analyze(formula):
    B, M, A, R, C, g, d = read(formula)
    a, r, p = map(affine, (A, R, g))
    if p.degree() != 1:
        raise UnsupportedCondition(
            "the exponential coordinate must have a nonconstant affine exponent"
        )
    factors = [vector(b) for b in (M, B, C)]
    if any(
        a.nth(1) * factors[0].get(prime, 0)
        - r.nth(1) * factors[1].get(prime, 0)
        - p.nth(1) * factors[2].get(prime, 0)
        != 0
        for prime in set().union(*factors)
    ):
        raise UnsupportedCondition(
            "the positive exponential quotient must have exactly the same variable part as the logarithm argument"
        )
    K = sp.simplify(B ** r.nth(0) * C ** p.nth(0) / M ** a.nth(0))
    if K.is_Rational is not True or K <= 0:
        raise UnsupportedCondition("the remaining positive bound must be rational")
    polynomial(K)
    stage = comparison(X**2 - d * X - K, "<=")
    domain = sp.Interval.open(d, sp.oo)
    positive = stage.solution.intersect(domain)
    _, back = back_substitute(C, g, (d, *stage.zeros))
    mapping = {t: branches[0] for t, _, branches in back}
    solution = inverse(positive, mapping, p.LC() > 0)
    return LogarithmExponential(
        B, M, A, R, C, g, d, K, stage, domain, positive, solution, tuple(back)
    )
