"""One exact equal-principal schedule for rate bounds, maturity and total payments."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..probability.solution_diagrams import repair
from . import loan_reference
from .common import UnsupportedCondition
from .differentiated_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    periods: int
    rate: sp.Rational
    debts: tuple
    payments: tuple
    total: sp.Rational
    result: sp.Rational


def schedule(capital, rate, periods):
    debts = tuple(capital * (periods - j) / periods for j in range(periods + 1))
    payments = tuple(debts[j] * (1 + rate / 100) - debts[j + 1] for j in range(periods))
    if (
        debts[-1] != 0
        or any(p <= 0 for p in payments)
        or sum(payments) != capital + rate * capital * (periods + 1) / 200
    ):
        raise UnsupportedCondition(
            "the positive payments must close the debt and match accumulated interest exactly"
        )
    return debts, payments


def analyze(q):
    capital, rate, periods = q.capital, q.rate, q.periods
    if q.kind == "rate_bound":
        rate = sp.simplify(100 * (q.target * periods / capital - 1))
        if rate <= 0:
            raise UnsupportedCondition(
                "the requested bound must determine a positive minimum rate"
            )
    elif q.kind == "maximum":
        difference = q.target - capital * rate / 100
        if difference <= 0:
            raise UnsupportedCondition(
                "the maximum payment must exceed the first interest charge"
            )
        periods = sp.simplify(capital / difference)
    else:
        periods = sp.simplify(200 * (q.target - capital) / (rate * capital) - 1)
    if sp.sympify(periods).is_Integer is not True or not 1 <= periods <= 1000:
        raise UnsupportedCondition(
            "the loan must have a whole positive term of at most 1000 years"
        )
    periods = int(periods)
    debts, payments = schedule(capital, rate, periods)
    total = sp.simplify(sum(payments))
    if q.kind == "maximum" and payments[0] != q.target:
        raise UnsupportedCondition(
            "the reconstructed largest payment must match the condition"
        )
    if q.kind == "term" and total != q.target:
        raise UnsupportedCondition(
            "the reconstructed payments must reproduce the stated total"
        )
    if q.kind == "rate_bound" and payments[-1] != q.target:
        raise UnsupportedCondition(
            "the minimum rate must attain the last-payment bound"
        )
    result = {"maximum": total, "term": sp.Integer(periods), "rate_bound": rate}[q.kind]
    return Analysis(q, periods, rate, debts, payments, total, result)


def build_context_repair_plan(context):
    from .differentiated_proof import proof

    content, (condition, ans, solution), text = loan_reference.read(context)
    a = analyze(parse(text))
    if a.question.kind == "rate_bound" and content.get("assets"):
        raise UnsupportedCondition(
            "this last-payment method has no reference attachment"
        )
    html, keys = proof(a, content)
    return repair(condition, ans, solution, answer(a.result), html, keys)
