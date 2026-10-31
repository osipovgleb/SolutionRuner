"""One exact annuity equation for principal, total payments and refinancing."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..probability.solution_diagrams import repair
from .annuity_questions import Question, parse
from .common import UnsupportedCondition
from .loan_schedule import balances
from .math_common import read


@dataclass(frozen=True)
class Analysis:
    question: Question
    capital: sp.Rational
    payment: sp.Rational
    factor: sp.Rational
    debts: tuple
    result: sp.Rational


def analyze(q):
    k, periods = 1 + q.rate / 100, q.periods
    weights = sum(k**j for j in range(periods))
    capital = q.capital if q.capital is not None else q.payment * weights / k**periods
    payment = q.payment if q.payment is not None else capital * k**periods / weights
    debts = balances(capital, k, (payment,) * periods)
    if q.style == "principal":
        result = capital * 1_000_000
    elif q.style == "refinance":
        new_payment = debts[1] * (1 + q.new_rate / 100)
        result = sp.simplify(payment - new_payment)
        if result != debts[1] * (q.rate - q.new_rate) / 100 or result <= 0:
            raise UnsupportedCondition(
                "savings must equal the reduced interest on the remaining debt"
            )
    else:
        result = periods * payment
    return Analysis(q, capital, payment, k, tuple(debts), result)


def build_context_repair_plan(context):
    from .annuity_proof import proof

    condition, ans, solution, text = read(context)
    a = analyze(parse(text))
    return repair(condition, ans, solution, answer(a.result), proof(a), ())
