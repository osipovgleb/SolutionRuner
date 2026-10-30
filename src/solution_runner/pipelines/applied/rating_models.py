"""Normalization constants and customer/expert ratings from checked laws."""

from dataclasses import dataclass, replace

import sympy as sp

from ..calculus.common import answer
from ..equations.logarithm_arithmetic import power
from ..probability.common import UnsupportedCondition, finish, rewrite
from ..triangles.isosceles.planner import _normalized_content, _section
from . import common, rating_condition, rating_proof
from .rating_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    result: sp.Rational
    numerator: sp.Rational
    denominator: sp.Expr
    exponent: sp.Rational | None = None


def analyze(q):
    v = q.values
    if q.kind.startswith("store_"):
        exponent = v["count"] / (50 * (v["buyer"] + sp.Rational(1, 10)))
        denominator = (
            power(v["count"] + 1, exponent)
            if q.kind == "store_power"
            else (v["count"] + 1) * exponent
        )
        if denominator == 0:
            raise UnsupportedCondition("the store-rating denominator must be nonzero")
        numerator = v["buyer"] - v["expert"]
        result = sp.simplify(v["buyer"] - numerator / denominator)
    else:
        exponent = None
        total = sum(v["weights"])
        if q.kind == "identity":
            if v["lower"] == v["upper"] == 0:
                raise UnsupportedCondition(
                    "a zero-only scale cannot determine A uniquely"
                )
            numerator, denominator = sp.Integer(total), sp.Integer(1)
        else:
            numerator, denominator = v["upper"] * total, v["target"]
            if denominator == 0:
                raise UnsupportedCondition(
                    "a zero target cannot determine positive A uniquely"
                )
        result = numerator / denominator
        if result <= 0:
            raise UnsupportedCondition(
                "the rating normalization constant must be positive"
            )
    if result.is_Rational is not True:
        raise UnsupportedCondition(
            "the exact rating answer must be rational without rounding"
        )
    return Analysis(q, result, numerator, denominator, exponent)


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    result = finish(condition, ans, solution, answer(a.result), rating_proof.proof(a))
    if a.question.repair_weight:
        original = _section(_normalized_content(context), "condition")
        corrected = rating_condition.repaired(original["html"])
        return replace(
            result,
            condition_html=corrected,
            transformations=(
                rewrite(original, "condition", "Условие", corrected),
                *result.transformations,
            ),
        )
    return result
