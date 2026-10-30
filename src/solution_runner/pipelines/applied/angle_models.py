"""Exact attained extrema on reviewed sine, cosine and cotangent branches."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer, real_roots
from ..probability.common import UnsupportedCondition, finish
from . import angle_proof, common
from .angle_questions import Question, X, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    feasible_values: sp.Set
    boundary: sp.Expr
    angle: sp.Rational
    result: sp.Rational


def value_domain(q):
    if q.function == "ctg":
        return sp.Interval.open(0, sp.oo)
    if q.function == "cos":
        return sp.Interval.open(0, 1)
    return sp.Interval(
        0,
        1,
        left_open=q.domain.left_open,
        right_open=q.domain.right_open if q.domain.end == 90 else False,
    )


def analyze(q):
    domain = value_domain(q)
    for denominator in q.denominators:
        if denominator.free_symbols - {X}:
            raise UnsupportedCondition(
                "an original angle denominator has an unassigned parameter"
            )
        p = sp.Poly(sp.fraction(sp.together(denominator))[0], X)
        if (
            p.is_zero
            or p.degree() > 2
            or p.degree()
            and any(domain.contains(r) is sp.S.true for r in real_roots(p.as_expr(), X))
        ):
            raise UnsupportedCondition(
                "an original denominator vanishes in the physical domain"
            )
    relation = {"eq": sp.Eq, "ge": sp.Ge, "le": sp.Le}[q.relation](
        q.expression, q.target
    )
    feasible = sp.solve_univariate_inequality(relation, X, relational=False).intersect(
        domain
    )
    if feasible is sp.S.EmptySet:
        raise UnsupportedCondition("no physical angle meets the requested level")
    upper = q.maximum == (q.function == "sin")
    boundary = feasible.sup if upper else feasible.inf
    if feasible.contains(boundary) is not sp.S.true:
        raise UnsupportedCondition("the requested angular extremum must be attained")
    radians = {"sin": sp.asin, "cos": sp.acos, "ctg": lambda x: sp.atan(1 / x)}[
        q.function
    ](boundary)
    angle = sp.simplify(180 * radians / sp.pi)
    if angle.is_Rational is not True:
        raise UnsupportedCondition(
            "the exact angle must be rational degrees without rounding"
        )
    if q.domain.contains(angle) is not sp.S.true:
        raise UnsupportedCondition("the inverse angle is outside its physical domain")
    return Analysis(q, feasible, boundary, angle, angle * q.multiplier)


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), angle_proof.proof(a))
