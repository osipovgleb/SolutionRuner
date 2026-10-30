"""Exact binary-log relations share one inversion and explicit physical domains."""

from dataclasses import dataclass, replace

import sympy as sp

from ..calculus.common import answer
from ..equations.logarithm_arithmetic import log_ratio, power
from ..probability.common import UnsupportedCondition, finish, rewrite
from ..triangles.isosceles.planner import _normalized_content, _section
from . import common, decay_condition, log_proof
from .log_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    result: sp.Rational
    exponent: sp.Rational
    factor: sp.Rational | None = None


def analyze(q):
    v = q.values
    if q.kind == "decay":
        exponent = log_ratio(sp.Integer(2), v["initial"] / v["target"])
        result = q.scale * exponent
        factor = None
    else:
        exponent = v["level"] / q.scale
        factor = power(sp.Integer(2), exponent)
        offset = v.get("offset", sp.Integer(0))
        result = (
            v["initial"] * factor
            if q.kind == "bell_pressure"
            else offset + (v["initial"] - offset) / factor
        )
        if result <= offset:
            raise UnsupportedCondition(
                "the logarithmic denominator must remain strictly positive"
            )
    if result.is_Rational is not True or result < 0 and q.kind != "water":
        raise UnsupportedCondition(
            "the exact physical answer must be rational without rounding"
        )
    return Analysis(q, result, exponent, factor)


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    result = finish(condition, ans, solution, answer(a.result), log_proof.proof(a))
    if a.question.repair_decay:
        original = _section(_normalized_content(context), "condition")
        corrected = decay_condition.repaired(original["html"])
        return replace(
            result,
            condition_html=corrected,
            transformations=(
                rewrite(original, "condition", "Условие", corrected),
                *result.transformations,
            ),
        )
    return result
