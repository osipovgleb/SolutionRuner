"""Exact base-range proofs and variable-base sign cases over one logarithm parser."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_power_inequality import rational_polynomial
from .exam_exponential import back_substitute
from .exponential_inequality_common_base import read_terms, vector
from .logarithm_exponential_input import ExponentialLogParser
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_substitution_preimages import comparison, excluded_points
from .variable_logarithm_parser import Atoms


@dataclass(frozen=True)
class RadicalRange:
    base: sp.Expr
    radicals: tuple
    denominator: sp.Expr
    constant: sp.Expr
    offset: sp.Expr
    exponential_base: sp.Expr
    lower: sp.Expr
    upper: sp.Expr
    poles: tuple
    domain: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution, endpoint=self.endpoint)

    def endpoint(self, value):
        if value.is_Rational:
            return sp.latex(value)
        if value in (self.lower, self.upper):
            argument = (
                self.offset if value == self.upper else self.offset - self.constant
            )
            return (
                r"\log_{" + sp.latex(self.exponential_base) + "}" + sp.latex(argument)
            )
        return sp.latex(value)


def base_range(base):
    numerator, denominator = sp.fraction(sp.together(base))
    terms = numerator.args if numerator.is_Add else ()
    if (
        denominator.is_Integer is not True
        or not 1 <= denominator <= 100
        or len(terms) != 2
        or any(
            not t.is_Pow
            or t.exp != sp.Rational(1, 2)
            or t.base.is_Integer is not True
            or not 1 < t.base <= 100
            for t in terms
        )
    ):
        raise UnsupportedCondition(
            "the parent base must be a bounded sum of two integer square roots over an integer"
        )
    p, q = sorted(t.base for t in terms)
    H = denominator**2 + p - q
    if denominator**2 <= p or H <= 0 or 4 * denominator**2 * p <= H**2:
        raise UnsupportedCondition(
            "both safe squarings must prove the full logarithm base greater than one"
        )
    return (p, q), denominator


def radical_range(left, right, atoms, denominators):
    first, second = atoms
    base = sp.cancel(first.base)
    if (
        left.value != first.symbol
        or right.value != second.symbol
        or sp.cancel(second.base - base) != 0
    ):
        raise UnsupportedCondition(
            "both complete logarithms must have the same original base"
        )
    radicals, denominator = base_range(base)
    K = sp.cancel(first.argument)
    argument = sp.cancel(second.argument)
    powers = [p for p in argument.atoms(sp.Pow) if p.exp.has(X)]
    if K.is_Rational is not True or not 0 < K <= 10**6 or len(powers) != 1:
        raise UnsupportedCondition(
            "the first argument must be positive constant and the second one constant minus one exponential"
        )
    (power,) = powers
    A = power.base
    C = sp.cancel(argument + power)
    if (
        power.exp != X
        or A.is_Rational is not True
        or A <= 1
        or C.is_Rational is not True
        or not K < C <= 10**6
    ):
        raise UnsupportedCondition(
            "the whole increasing exponential argument must have two ordered positive thresholds"
        )
    vector(A)
    _, back = back_substitute(A, X, (C - K, C))
    lo, hi = (row[2][0] for row in back)
    poles = excluded_points(denominators)
    domain = sp.Interval.open(-sp.oo, hi) - sp.FiniteSet(*poles)
    solution = sp.Interval.Ropen(lo, hi) - sp.FiniteSet(*poles)
    return RadicalRange(
        base, radicals, denominator, K, C, A, lo, hi, poles, domain, solution
    )


@dataclass(frozen=True)
class VariableRange:
    base: sp.Expr
    argument: sp.Expr
    coefficient: sp.Expr
    center: sp.Expr
    square_coefficient: sp.Expr
    poles: tuple
    domain: object
    stage: object
    cases: tuple
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def variable_range(left, right, atoms, denominators):
    (atom,) = atoms
    coefficient, log = left.children
    B, Q, C = map(sp.cancel, (atom.base, atom.argument, coefficient.value))
    if log.kind != "logarithm" or log.value != atom.symbol or right.value != 0:
        raise UnsupportedCondition(
            "the whole product must be one affine coefficient times one complete variable-base logarithm"
        )
    b = rational_polynomial(B, 1)
    c = rational_polynomial(C, 1)
    q = rational_polynomial(Q - 1, 2)
    center = -q.nth(1) / (2 * q.nth(2))
    if (
        b.LC() <= 0
        or c.LC() <= 0
        or q.LC() <= 0
        or sp.discriminant(q) != 0
        or B.subs(X, center) != 1
        or C.subs(X, center) <= 0
    ):
        raise UnsupportedCondition(
            "the parent sign method needs an upward square plus one and the same forbidden base-one point"
        )
    poles = excluded_points((*denominators, B - 1))
    domain = comparison(B, ">", denominators=denominators).solution - sp.FiniteSet(
        *poles
    )
    stage = comparison(C * (B - 1), ">=")
    cases = tuple(
        (
            sign,
            domain.intersect(comparison(B - 1, op).solution).intersect(
                comparison(C, ">=" if sign == 1 else "<=").solution
            ),
        )
        for sign, op in ((1, ">"), (-1, "<"))
    )
    solution = sp.Union(*(s for _, s in cases))
    return VariableRange(B, Q, C, center, q.LC(), poles, domain, stage, cases, solution)


def analyze(formula):
    atoms = Atoms()
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: ExponentialLogParser(text, atoms=atoms)
    )
    if operator != ">=":
        raise UnsupportedCondition(
            "the reviewed monotonicity parent uses a closed greater-than comparison"
        )
    if len(atoms.values) == 2 and left.kind == right.kind == "logarithm":
        return radical_range(left, right, atoms.values, denominators)
    if len(atoms.values) == 1 and left.kind == "multiply" and right.kind == "scalar":
        return variable_range(left, right, atoms.values, denominators)
    raise UnsupportedCondition(
        "the entire input must match a certified logarithm comparison or variable-base product"
    )
