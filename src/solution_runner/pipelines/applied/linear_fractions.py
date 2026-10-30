"""Exact linear-fraction constraints intersected with their physical domains."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer, real_roots
from ..probability.common import UnsupportedCondition, finish
from . import common, fraction_proof
from .fraction_questions import Question, X, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    feasible: sp.Set
    result: sp.Rational


def check_denominators(q):
    for denominator in q.denominators:
        if denominator.free_symbols - {X}:
            raise UnsupportedCondition(
                "an original denominator has an unassigned parameter"
            )
        numerator = sp.fraction(sp.together(denominator))[0]
        p = sp.Poly(numerator, X)
        if p.is_zero:
            raise UnsupportedCondition("an original denominator is zero")
        if p.degree() > 2:
            raise UnsupportedCondition(
                "an original denominator exceeds the reviewed degree"
            )
        if p.degree() and any(
            q.domain.contains(r) is sp.S.true for r in real_roots(numerator, X)
        ):
            raise UnsupportedCondition(
                "an original denominator vanishes inside the physical domain"
            )


def analyze(q):
    check_denominators(q)
    numerator, denominator = sp.fraction(sp.cancel(q.expression - q.target))
    if any(sp.Poly(p, X).degree() > 1 for p in [numerator, denominator]):
        raise UnsupportedCondition("a linear numerator and denominator are required")
    relation = {"eq": sp.Eq, "le": sp.Le, "ge": sp.Ge}[q.relation](
        q.expression, q.target
    )
    feasible = sp.solve_univariate_inequality(relation, X, relational=False).intersect(
        q.domain
    )
    if feasible is sp.S.EmptySet:
        raise UnsupportedCondition("no physical value meets the requested level")
    result = feasible.sup if q.maximum else feasible.inf
    if result.is_Rational is not True or feasible.contains(result) is not sp.S.true:
        raise UnsupportedCondition(
            "the requested extremum must be finite, rational and attained"
        )
    return Analysis(q, feasible, result)


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(a.result), fraction_proof.proof(a))
