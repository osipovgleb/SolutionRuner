"""Exact intersections of periodic level intervals with the observation window."""

from dataclasses import dataclass
from fractions import Fraction

import sympy as sp

from ..calculus.common import answer
from ..probability.common import UnsupportedCondition, finish, rounded
from . import common, window_proof
from .window_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    ratio: sp.Rational
    base: tuple[sp.Rational, sp.Rational] | None
    times: sp.Set
    duration: sp.Rational
    fraction: sp.Rational
    result: sp.Rational


def periodic_times(q, lower, upper):
    first = sp.ceiling((q.phase - upper) / 360)
    last = sp.floor((q.phase + q.frequency * q.window - lower) / 360)
    if last - first > 100:
        raise UnsupportedCondition(
            "too many periodic intervals for a reviewed finite-window proof"
        )
    pieces = [
        sp.Interval(
            (lower + 360 * n - q.phase) / q.frequency,
            (upper + 360 * n - q.phase) / q.frequency,
            left_open=q.strict,
            right_open=q.strict,
        ).intersect(sp.Interval(0, q.window))
        for n in range(int(first), int(last) + 1)
    ]
    return sp.Union(*pieces)


def analyze(q):
    ratio = q.level / q.amplitude
    base = None
    if ratio > 1 or ratio == 1 and q.strict:
        times = sp.S.EmptySet
    elif ratio < -1 or ratio == -1 and not q.strict:
        times = sp.Interval(0, q.window)
    else:
        angle = sp.simplify(
            180 * {"sin": sp.asin, "cos": sp.acos}[q.function](ratio) / sp.pi
        )
        if angle.is_Rational is not True:
            raise UnsupportedCondition(
                "an exact rational-degree level angle is required"
            )
        base = (angle, 180 - angle) if q.function == "sin" else (-angle, angle)
        times = periodic_times(q, *base)
    duration = times.measure
    fraction = duration / q.window
    result = fraction * (100 if q.kind == "sensor" else 1)
    return Analysis(q, ratio, base, times, duration, fraction, result)


def rendered_answer(a):
    if a.question.kind == "sensor":
        return answer(a.result)
    return answer(sp.Rational(rounded(Fraction(a.result), 2).replace(",", ".")))


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, analysis = calculate(context)
    condition, ans, solution, _ = data
    result = rendered_answer(analysis)
    return finish(
        condition, ans, solution, result, window_proof.proof(analysis, result)
    )
