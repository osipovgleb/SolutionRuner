"""Prove the modulus power identity on both sides of zero before comparing arguments."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .absolute_log_power_input import AbsoluteLogPowerReader
from .absolute_power_inequality import rational_polynomial
from .exponential_inequality_common_base import read_terms, vector
from .logarithm_arithmetic import log_ratio, power
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_substitution_preimages import comparison, excluded_points


@dataclass(frozen=True)
class AbsoluteLogPower:
    base: sp.Expr
    reference: sp.Expr
    shift: sp.Expr
    coefficients: tuple
    total: sp.Expr
    argument: sp.Expr
    stage: object
    poles: tuple
    domain: object
    solution: object

    @property
    def answer(self):
        return set_latex(self.solution)


def analyze(formula):
    values, logs = {}, {}
    left, right, denominators, operator = read_terms(
        formula, reader=lambda text: AbsoluteLogPowerReader(text, values, logs)
    )
    if (
        left.kind != "weighted_sum"
        or right.kind != "weighted_power"
        or len(values) != 1
        or next(iter(values.values())) != X
        or operator != "<="
    ):
        raise UnsupportedCondition(
            "the parent compares a complete numeric/modulus power sum with one weighted reciprocal-base power"
        )
    (c1, first), (c2, second) = left.children
    total, third = right.children
    A, exponent = (n.value for n in first.children)
    modulus, second_exponent = second.children
    inverse, third_exponent = (n.value for n in third.children)
    if (
        A.is_Rational is not True
        or A <= 1
        or modulus.kind != "absolute"
        or modulus.value not in values
    ):
        raise UnsupportedCondition(
            "the first base must be increasing numeric and the second the complete modulus of x"
        )
    vector(A)
    first_log, second_log, third_log = (
        logs[s] for s in (exponent, second_exponent.value, third_exponent)
    )
    b = first_log.base
    if (
        b.is_Rational is not True
        or not 1 < b <= 1000
        or first_log.argument != X**2
        or second_log.base != b
        or second_log.argument != A**2
        or second_log.shift != 0
        or third_log.base != 1 / b
        or third_log.shift != 0
        or inverse != 1 / A
    ):
        raise UnsupportedCondition(
            "all logarithm arguments, bases and reciprocal identities must match the complete parent sum"
        )
    rational_polynomial(third_log.argument, 1)
    if sp.cancel(log_ratio(b, second_log.argument) - 2 * log_ratio(b, A)) != 0:
        raise UnsupportedCondition(
            "the full scalar exponent must prove the modulus power identity"
        )
    shifted = power(A, first_log.shift)
    if total != c1 * shifted + c2:
        raise UnsupportedCondition(
            "the whole positive coefficient sum must equal the right coefficient"
        )
    original = (*denominators, X)
    poles = excluded_points(original)
    domain = comparison(third_log.argument, ">", denominators=original).solution
    stage = comparison(X**2 - third_log.argument, "<=")
    return AbsoluteLogPower(
        A,
        b,
        first_log.shift,
        (c1, c2),
        total,
        third_log.argument,
        stage,
        poles,
        domain,
        stage.solution.intersect(domain),
    )
