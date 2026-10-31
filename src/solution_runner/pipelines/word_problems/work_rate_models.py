"""Production and filling rates use the shared exact time-balance solver."""

import sympy as sp

from ..calculus.common import answer
from ..probability.common import finish
from . import work_pair_assets, work_rate_questions
from .motion_models import Analysis
from .time_balance import Balance, X, solve
from .work_combined_models import BUILDERS


def analyze(q):
    if q.kind in BUILDERS:
        b = BUILDERS[q.kind](q)
        return Analysis(q, b, *solve(b))
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
    data = work_pair_assets.read(context)
    q = work_rate_questions.parse(data[3])
    work_pair_assets.validate(context, q)
    return data, analyze(q)


def build_context_repair_plan(context):
    from .work_rate_proof import proof

    data, a = calculate(context)
    condition, ans, _, _ = data
    solution = next(
        (
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "solution"
        ),
        None,
    )
    if a.question.kind == "work_pairs_boys":
        from ..probability.solution_diagrams import repair

        markup, keys, changes = work_pair_assets.prepare(context, a.question)
        return repair(
            condition,
            ans,
            solution,
            answer(a.result),
            proof(a, diagram=markup),
            keys,
            changes,
        )
    return finish(condition, ans, solution, answer(a.result), proof(a))
