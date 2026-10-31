"""One prescribed-debt schedule for payment bounds, total interest and principal."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..probability.solution_diagrams import repair
from .common import UnsupportedCondition
from .debt_schedule_questions import Question, parse
from .debt_table_reader import read
from .loan_schedule import balances


@dataclass(frozen=True)
class Analysis:
    question: Question
    factor: sp.Rational
    payments: tuple
    total: sp.Rational
    coefficient: sp.Rational
    result: sp.Rational


def satisfies(q, coefficient, value):
    amount = coefficient * value
    return {
        "меньше": amount < q.limit,
        "не больше": amount <= q.limit,
        "больше": amount > q.limit,
        "не меньше": amount >= q.limit,
    }[q.bound]


def analyze(q):
    k = 1 + q.rate / 100
    payments = tuple(k * a - b for a, b in zip(q.ratios, q.ratios[1:]))
    if balances(sp.Integer(1), k, payments) != q.ratios:
        raise UnsupportedCondition(
            "reconstructed payments must reproduce all stated debt fractions"
        )
    total = sum(payments)
    if total != 1 + q.rate / 100 * sum(q.ratios[:-1]):
        raise UnsupportedCondition(
            "total payments must equal principal plus interest on all balances"
        )
    coefficient = total
    if q.kind == "monthly":
        result = (total - 1) * 100
    elif q.kind == "geometric":
        result = q.limit / total
    else:
        if q.scope == "каждая из выплат":
            coefficient = max(payments) if q.extreme == "наибольшее" else min(payments)
        boundary = q.limit / coefficient
        result = {
            "меньше": sp.ceiling(boundary) - 1,
            "не больше": sp.floor(boundary),
            "больше": sp.floor(boundary) + 1,
            "не меньше": sp.ceiling(boundary),
        }[q.bound]
        neighbor = result + (1 if q.extreme == "наибольшее" else -1)
        if (
            result < 1
            or not satisfies(q, coefficient, result)
            or satisfies(q, coefficient, neighbor)
        ):
            raise UnsupportedCondition(
                "the positive integer extremum must satisfy the bound and exclude its neighbor"
            )
    return Analysis(q, k, payments, total, coefficient, result)


def build_context_repair_plan(context):
    from .debt_schedule_proof import proof

    condition, ans, solution, text, tables = read(context)
    a = analyze(parse(text, tables))
    return repair(condition, ans, solution, answer(a.result), proof(a), ())
