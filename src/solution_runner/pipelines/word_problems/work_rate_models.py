"""Production and filling rates use the shared exact time-balance solver."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import finish
from . import math_common, work_rate_questions
from .motion_models import Analysis
from .time_balance import Balance, X, solve


def analyze(q):
    v = q.values
    slow, fast = (X - v["gap"], X) if q.target_fast else (X, X + v["gap"])
    domain = sp.Interval.open(v["gap"] if q.target_fast else 0, sp.oo)
    b = Balance(
        v["fast_amount"] / fast + v["delay"],
        v["slow_amount"] / slow,
        domain,
        (fast, slow),
    )
    return Analysis(q, b, *solve(b))


def calculate(context):
    data = math_common.read(context)
    return data, analyze(work_rate_questions.parse(data[3]))


def build_context_repair_plan(context):
    from .work_rate_proof import proof

    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), proof(a))
