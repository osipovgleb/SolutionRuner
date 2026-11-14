"""Prove the positive-variable power identity before solving one log coordinate."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exponential_inequality_common_base import read_terms, vector
from .logarithm_arithmetic import log_ratio
from .logarithm_rational_substitution import analyze_transformed
from .logarithmic_power_input import LogarithmicPowerParser, T
from .rational_inequality import set_latex
from .rational_inequality_parser import X
from .rational_inequality_proof import RELATION

METHODS = ("linear_reciprocity", "square_coordinate")


@dataclass(frozen=True)
class LogarithmicPower:
    method: str
    operator: str
    base: sp.Expr
    reference: sp.Expr
    exponent: sp.Expr
    second_exponent_text: str
    right: sp.Expr
    level: sp.Expr
    inverse: object
    decimal_log: bool

    @property
    def answer(self):
        return set_latex(self.inverse.solution)


def analyze(formula, method):
    if method not in METHODS:
        raise UnsupportedCondition(
            "a reviewed power-logarithm proof method is required"
        )
    state = {"base": None, "logs": 0}
    left, right, _, operator = read_terms(
        formula, reader=lambda text: LogarithmicPowerParser(text, state=state)
    )
    if (
        left.kind != "add"
        or any(n.kind != "power" for n in left.children)
        or right.value.free_symbols
        or right.value.is_positive is not True
        or state["base"] is None
    ):
        raise UnsupportedCondition(
            "one complete sum of two powers and a positive scalar bound is required"
        )
    first, second = left.children
    base = first.children[0].value
    reference = state["base"]
    if (
        base.is_Rational is not True
        or base <= 1
        or second.children[0].kind != "variable"
    ):
        raise UnsupportedCondition(
            "the first increasing constant base and the second complete variable base must match the parent"
        )
    vector(base)
    exponent = first.children[1].value
    projected = sp.cancel(log_ratio(base, reference) * T * second.children[1].value)
    expected = T if method == "linear_reciprocity" else T**2
    if exponent != expected or sp.cancel(projected - exponent) != 0:
        raise UnsupportedCondition(
            "the two complete power terms must coincide on the positive-variable domain"
        )
    level = log_ratio(base, sp.simplify(right.value / 2))
    if (
        level.is_Rational is not True
        or abs(level) > 30
        or level.q > 100
        or (method == "square_coordinate" and level <= 0)
    ):
        raise UnsupportedCondition(
            "a bounded exact power threshold matching the parent's logarithm method is required"
        )
    transformed = sp.latex(exponent.subs(T, X) - level) + RELATION[operator] + "0"
    inverse = analyze_transformed(reference, (), transformed)
    return LogarithmicPower(
        method,
        operator,
        base,
        reference,
        exponent,
        second.children[1].text,
        right.value,
        level,
        inverse,
        r"\lg" in formula,
    )
