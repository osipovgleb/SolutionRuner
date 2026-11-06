"""Exact rational inequality in one positive exponential substitution."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exam_exponential_proof import labels
from .exam_scalar import compare
from .exponential_inequality_common_base import read_terms
from .exponential_inequality_quadratic import inverse, normalize_powers
from .rational_exponential_input import leaves, original_domains, substitute
from .rational_inequality import analyze as rational
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION
from .rational_inequality_roots import ordered


@dataclass(frozen=True)
class RationalExponential:
    formula: str
    operator: str
    original: sp.Expr
    powers: tuple
    base: sp.Expr
    exponent: sp.Expr
    stage: object
    positive_solution: object
    back: tuple
    extra_poles: tuple
    domain: object
    solution: object

    def endpoint(self, value):
        if self.exponent == -X and value.has(sp.log):
            for t, _, roots in self.back:
                if roots == (value,):
                    return r"-\log_{" + sp.latex(self.base) + "}(" + sp.latex(t) + ")"
        return labels(self, number_formatter=sp.latex, preserve_offset=True).get(
            value, sp.latex(value)
        )

    @property
    def answer(self):
        return set_latex(self.solution, endpoint=self.endpoint)


def analyze(formula):
    left, right, denominators, operator = read_terms(formula)
    powers = leaves(left) + leaves(right)
    if not 1 <= len(powers) <= 24:
        raise UnsupportedCondition(
            "one to twenty-four typed exponential leaves are required"
        )
    base, exponent, _ = normalize_powers(
        [(sp.Integer(1), *(c.value for c in node.children)) for node in powers],
        sp.Integer(0),
    )
    stage = rational(
        substitute(left, base, exponent)
        + RELATION[operator]
        + substitute(right, base, exponent)
    )
    original_t_poles, original_x_poles = original_domains(denominators, base, exponent)
    if any(compare(t, 0) > 0 and t not in stage.poles for t in original_t_poles):
        raise UnsupportedCondition(
            "rational substitution must retain every original positive denominator root"
        )
    positive = stage.solution.intersect(sp.Interval.open(0, sp.oo))
    _, back = back_substitute(
        base, exponent, tuple(t for t in stage.points if compare(t, 0) > 0)
    )
    if any(len(points) != 1 for _, _, points in back):
        raise UnsupportedCondition(
            "the affine substitution must have one inverse per positive boundary"
        )
    mapping = {t: points[0] for t, _, points in back}
    extra_poles = ordered(original_x_poles)
    domain = sp.S.Reals - sp.FiniteSet(*extra_poles)
    solution = inverse(positive, mapping, sp.diff(exponent, X) > 0).intersect(domain)
    return RationalExponential(
        formula,
        operator,
        left.value - right.value,
        powers,
        base,
        exponent,
        stage,
        positive,
        tuple(back),
        extra_poles,
        domain,
        solution,
    )
