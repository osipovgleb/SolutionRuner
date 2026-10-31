"""Recover a and b from table-angle coordinates and compute the requested value."""

import re
from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer
from ..core.errors import ContentPlanError
from ..equations.trig_angles import parse_angle
from ..probability.common import finish
from ..triangles.isosceles.planner import _normalized_content, _section
from . import trig_svg
from .graph_questions import read

FUNCTIONS = {"cos": sp.cos, "sin": sp.sin, "tan": sp.tan}


@dataclass(frozen=True)
class Question:
    function: str
    kind: str
    whole: bool = False
    target: sp.Expr | None = None


def parse(context):
    forms, text = read(context)
    match = re.fullmatch(r"f\(x\)=a\\(cos|sin|tg)x\+b", forms[0]) if forms else None
    if not match:
        raise ContentPlanError("a complete a trig(x)+b graph formula is required")
    function = "tan" if match[1] == "tg" else match[1]
    prefix = r"На рисунке изображен график функции @0@"
    if len(forms) == 1:
        question = re.fullmatch(prefix + r"\s*\.\s*Найдите (a|b)\s*\.", text)
        if question:
            return Question(function, question[1])
    if len(forms) == 2 and re.fullmatch(
        prefix + r"\s*,\s*где a и b — целые числа\s*\.\s*Найдите @1@\s*\.", text
    ):
        target = re.fullmatch(r"(?:y|f)\((.+)\)", forms[1])
        if target:
            coefficient, degrees = parse_angle(target[1])
            if degrees:
                raise ContentPlanError(
                    "this graph question requires a rational-pi argument"
                )
            return Question(function, "value", True, coefficient * sp.pi)
    raise ContentPlanError("the entire trigonometric graph question must match")


@dataclass(frozen=True)
class Analysis:
    question: Question
    zero: tuple
    probe: tuple
    coefficient: sp.Rational
    shift: sp.Rational
    result: sp.Rational


def analyze(question, points):
    function = FUNCTIONS[question.function]
    zeros = [p for p in points if function(p[0]) == 0]
    probes = [p for p in points if function(p[0]) in (-1, 1)]
    if not zeros or not probes:
        raise ContentPlanError(
            "the inspected graph needs a zero-angle and a unit-angle reading"
        )
    priority = sp.pi if question.whole and question.function == "sin" else sp.Integer(0)
    zero = min(zeros, key=lambda p: (abs(p[0] - priority), p[0]))
    probe = min(probes, key=lambda p: (abs(p[0]), p[0]))
    shift = zero[1]
    coefficient = sp.simplify((probe[1] - shift) / function(probe[0]))
    if (
        coefficient.is_Rational is not True
        or shift.is_Rational is not True
        or coefficient == 0
    ):
        raise ContentPlanError(
            "one nonconstant exact trigonometric graph must be determined"
        )
    if any(sp.simplify(coefficient * function(x) + shift - y) != 0 for x, y in points):
        raise ContentPlanError(
            "all inspected points must agree with the recovered trigonometric formula"
        )
    if question.whole and any(v.is_Integer is not True for v in (coefficient, shift)):
        raise ContentPlanError(
            "both coefficients explicitly declared integer must be integral"
        )
    result = {"a": coefficient, "b": shift}.get(question.kind)
    if question.kind == "value":
        result = sp.simplify(coefficient * function(question.target) + shift)
    if result is None or result.is_Rational is not True:
        raise ContentPlanError(
            "the requested trigonometric value must be an exact rational"
        )
    return Analysis(question, zero, probe, coefficient, shift, result)


def build_context_repair_plan(
    context, *, condition_asset_bytes, current_asset_content_type
):
    from .trig_proof import proof

    question = parse(context)
    points = trig_svg.read(
        context, condition_asset_bytes, current_asset_content_type, question.function
    )
    a = analyze(question, points)
    content = _normalized_content(context)
    condition, ans, solution = (
        _section(content, k) for k in ("condition", "answer", "solution")
    )
    return finish(condition, ans, solution, answer(a.result), proof(a))
