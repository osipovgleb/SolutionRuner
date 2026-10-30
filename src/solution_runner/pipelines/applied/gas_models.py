"""Positive fractional powers and factor comparisons reuse exact prime-log algebra."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..equations.logarithm_arithmetic import log_ratio, power
from ..probability.common import UnsupportedCondition, finish
from . import common, gas_proof
from .gas_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    result: sp.Rational
    ratio: sp.Rational | None = None


def analyze(q):
    v = q.values
    if q.kind == "factor":
        result = log_ratio(v["volume_factor"], v["pressure_factor"])
        ratio = None
    elif q.kind == "absolute":
        ratio = v["constant"] / v["pressure"]
        result = power(ratio, 1 / v["exponent"])
    else:
        ratio = power(v["pressure"], 1 / v["exponent"])
        result = v["initial"] / ratio
    if result.is_Rational is not True or result <= 0:
        raise UnsupportedCondition(
            "the exact positive gas answer must be rational without rounding"
        )
    return Analysis(q, result, ratio)


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), gas_proof.proof(a))
