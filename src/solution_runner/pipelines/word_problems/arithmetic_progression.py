"""One arithmetic-series balance for elapsed days, last and intermediate terms."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..probability.common import finish
from . import math_common
from .common import UnsupportedCondition
from .progression_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    days: sp.Integer
    difference: sp.Rational | None
    last: sp.Rational | None
    result: sp.Rational


def analyze(q):
    v = q.values
    if "end_sum" in v:
        days = 2 * v["total"] / v["end_sum"]
        if days.is_Integer is not True or days < 2:
            raise UnsupportedCondition(
                "an increasing progression must span at least two whole days"
            )
        return Analysis(q, days, None, None, days)
    days, asked = v["days"], v["asked"]
    if (
        days.is_Integer is not True
        or days < 2
        or asked.is_Integer is not True
        or not 1 <= asked <= days
    ):
        raise UnsupportedCondition(
            "whole day counts and a requested day within the completed work are required"
        )
    difference = (2 * v["total"] / days - 2 * v["first"]) / (days - 1)
    if difference <= 0:
        raise UnsupportedCondition(
            "the daily arithmetic-progression increase must be positive"
        )
    if q.counted and any(
        x.is_Integer is not True for x in (v["total"], v["first"], difference)
    ):
        raise UnsupportedCondition(
            "tasks and cards require integer daily counts and an integer increase"
        )
    last = v["first"] + (days - 1) * difference
    result = v["first"] + (asked - 1) * difference
    return Analysis(q, days, difference, last, result)


def calculate(context):
    data = math_common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    from .progression_proof import proof

    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), proof(a))
