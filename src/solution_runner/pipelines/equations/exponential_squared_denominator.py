"""Keep polynomial zeros and rationalize an exact squared exponential denominator."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exponential_inequality_common_base import read_terms
from .exponential_inequality_quadratic import normalize_powers, power_terms
from .rational_exponential_figures import multiplicity
from .rational_inequality import analyze as rational
from .rational_inequality import set_latex
from .rational_inequality_methods import terms
from .rational_inequality_parser import X, polynomial
from .rational_inequality_proof import RELATION
from .rational_inequality_roots import real_roots


@dataclass(frozen=True)
class SquaredDenominator:
    formula: str
    operator: str
    numerator: sp.Expr
    denominator: sp.Expr
    base: sp.Expr
    exponent: sp.Expr
    coefficients: tuple
    scalar: sp.Expr
    root: sp.Expr
    level: sp.Expr
    stage: object

    @property
    def solution(self):
        return self.stage.solution

    @property
    def answer(self):
        return set_latex(self.solution)


def denominator_square(node):
    powers, constant = power_terms(terms(node))
    base, exponent, coefficients = normalize_powers(
        powers, constant, exponent_degree=2, preserve_shift=True
    )
    if set(coefficients) - {0, 1, 2}:
        raise UnsupportedCondition(
            "the denominator must be quadratic in one positive power"
        )
    p = polynomial(sum(c * X**k for k, c in coefficients.items()))
    if p.degree() != 2 or p.LC() <= 0 or sp.discriminant(p) != 0:
        raise UnsupportedCondition(
            "the exponential denominator must be an exact positive square"
        )
    root = -p.nth(1) / (2 * p.nth(2))
    if root <= 0:
        raise UnsupportedCondition(
            "the squared difference needs a positive exponential level"
        )
    _, back = back_substitute(base, exponent, (root,), quadratic_logs=True)
    if len(back) != 1 or back[0][1].is_Rational is not True:
        raise UnsupportedCondition(
            "the source rationalization needs an exact rational logarithmic level"
        )
    return base, exponent, tuple(sorted(coefficients.items())), p.LC(), root, back[0][1]


def analyze(formula):
    left, right, denominators, operator = read_terms(formula)
    if left.kind != "divide" or right.value != 0:
        raise UnsupportedCondition(
            "one polynomial over a squared exponential denominator is required"
        )
    numerator, denominator = left.children
    p = polynomial(numerator.value)
    if p.degree() != 3 or any(c.is_Rational is not True for c in p.all_coeffs()):
        raise UnsupportedCondition("the parent numerator must be a rational cubic")
    zeros = real_roots(p.as_expr())
    orders = [multiplicity(p.as_expr(), z) for z in zeros]
    if len(zeros) != 2 or sorted(orders) != [1, 2]:
        raise UnsupportedCondition(
            "the numerator needs one simple and one double real zero"
        )
    d = denominator.value
    if any(
        v.free_symbols and v != d and v.is_positive is not True for v in denominators
    ):
        raise UnsupportedCondition(
            "additional original denominators must be proved positive"
        )
    base, exponent, coefficients, scalar, root, level = denominator_square(denominator)
    stage = rational(
        r"\frac{"
        + sp.latex(p.as_expr())
        + "}{"
        + sp.latex((exponent - level) ** 2)
        + "}"
        + RELATION[operator]
        + "0"
    )
    rational_denominator = sp.fraction(stage.original)[1]
    if len(stage.poles) != 2 or any(
        multiplicity(rational_denominator, p) != 2 for p in stage.poles
    ):
        raise UnsupportedCondition(
            "the reviewed composition needs two distinct double poles"
        )
    if any(z in stage.poles for z in zeros):
        raise UnsupportedCondition(
            "the reviewed double zeros and double poles must be distinct"
        )
    return SquaredDenominator(
        formula,
        operator,
        p.as_expr(),
        d,
        base,
        exponent,
        coefficients,
        scalar,
        root,
        level,
        stage,
    )
