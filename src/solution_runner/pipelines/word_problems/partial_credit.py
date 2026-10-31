"""Solve exact annual loan equations for a missing amount or interest rate."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..probability.solution_diagrams import repair
from .common import UnsupportedCondition
from .loan_schedule import balances
from .math_common import read
from .partial_credit_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    capital: sp.Rational
    payment: sp.Rational
    last: sp.Rational
    factor: sp.Rational
    debts: tuple
    total: sp.Rational
    result: sp.Rational
    roots: tuple = ()


def analyze(q):
    if q.target == "rate":
        from .loan_rate import analyze as analyze_rate

        return analyze_rate(q)
    k = 1 + q.rate / 100
    weight = k**2 + k
    capital, payment, last = q.capital, q.payment, q.last
    if capital is None:
        capital = (last + weight * payment) / k**3
    elif payment is None:
        payment = (capital * k**3 - (q.total if q.total is not None else last)) / (
            weight - (2 if q.total is not None else 0)
        )
    if last is None:
        last = capital * k**3 - weight * payment
    debts = balances(capital, k, (payment, payment, last))
    total = 2 * payment + last
    if q.total is not None and total != q.total:
        raise UnsupportedCondition(
            "the reconstructed payments must reproduce the stated total"
        )
    result = {"first": payment, "last": last, "capital": capital, "total": total}[
        q.target
    ] * q.scale
    return Analysis(q, capital, payment, last, k, debts, total, result)


def build_context_repair_plan(context):
    from .partial_credit_proof import proof

    condition, ans, solution, text = read(context)
    a = analyze(parse(text))
    return repair(condition, ans, solution, answer(a.result), proof(a), ())
