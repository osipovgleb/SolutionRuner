"""Exact capitalization: beginning-of-year flows precede end-of-year interest."""

from dataclasses import dataclass

import sympy as sp

from .common import UnsupportedCondition
from .deposit_questions import Question, parse

X = sp.Symbol("x", real=True)


def balances(capital, rates, flow=sp.S.Zero):
    value = capital
    result = []
    for year, rate in enumerate(rates, 1):
        before = value + (flow if year > 1 else 0)
        if before.is_number and before < 0:
            raise UnsupportedCondition(
                "the withdrawal cannot exceed the current deposit"
            )
        value = sp.expand(before * (1 + rate / 100))
        result.append(value)
    return tuple(result)


@dataclass(frozen=True)
class Analysis:
    question: Question
    capital: sp.Rational
    rate: sp.Rational
    balances: tuple
    alternative: tuple
    result: sp.Rational


def analyze(text):
    q = parse(text)
    capital, rate = q.capital, q.rate
    if q.kind == "initial":
        expression = balances(X, (rate,) * q.periods, q.flow)[-1]
        coefficient = expression.coeff(X)
        constant = expression.subs(X, 0)
        capital = sp.simplify((q.final - constant) / coefficient)
        if capital <= 0:
            raise UnsupportedCondition("the original deposit must be strictly positive")
    if q.kind == "rate":
        factor = sp.simplify((q.final / capital) ** sp.Rational(1, q.periods))
        if factor.is_Rational is not True or factor < 1:
            raise UnsupportedCondition(
                "one exact rational nondecreasing annual factor is required"
            )
        rate = 100 * (factor - 1)
    values = balances(capital, (rate,) * q.periods, q.flow)
    if q.final is not None and values[-1] != q.final:
        raise UnsupportedCondition(
            "the reconstructed schedule must reproduce the final amount exactly"
        )
    alternative = ()
    if q.kind == "compare":
        alternative = balances(
            capital, tuple(q.first + i * q.step for i in range(q.periods))
        )
        if alternative[-1] == values[-1]:
            raise UnsupportedCondition(
                "the question must identify one strictly larger final deposit"
            )
        result = abs(values[-1] - alternative[-1]) * q.unit / q.output_unit
    elif q.kind == "initial":
        result = capital * q.unit / q.output_unit
    elif q.kind == "rate":
        result = rate
    else:
        result = values[-1] * q.unit / q.output_unit
    return Analysis(q, capital, rate, values, alternative, sp.simplify(result))
