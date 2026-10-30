"""Exact rational constraints intersected with their physical domains and ranges."""

from dataclasses import dataclass, replace

import sympy as sp

from ..calculus.common import answer, real_roots
from ..probability.common import UnsupportedCondition, finish, rewrite
from ..triangles.isosceles.planner import _normalized_content, _section
from . import common, fraction_proof, lens_condition
from .fraction_questions import Question, X, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    feasible: sp.Set
    result: sp.Rational
    repair_lens_wording: bool = False


def check_denominators(q):
    for denominator in q.denominators:
        if denominator.func == sp.Abs:
            denominator = denominator.args[0]
        if denominator.has(sp.Abs):
            raise UnsupportedCondition(
                "an original modulus must enclose a whole denominator"
            )
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
    degree = 2 if q.kind in ["resonance", "rocket"] else 1
    if any(sp.Poly(p, X).degree() > degree for p in [numerator, denominator]):
        raise UnsupportedCondition(
            "the rational constraint exceeds its reviewed degree"
        )
    relation = {"eq": sp.Eq, "le": sp.Le, "ge": sp.Ge}[q.relation](
        q.expression, q.target
    )
    feasible = sp.solve_univariate_inequality(relation, X, relational=False).intersect(
        q.domain
    )
    if q.lower_target is not None:
        lower = sp.solve_univariate_inequality(
            q.expression >= q.lower_target, X, relational=False
        )
        feasible = feasible.intersect(lower)
    if q.kind == "root_steps":
        feasible = feasible.intersect(sp.S.Naturals0)
    if feasible is sp.S.EmptySet:
        raise UnsupportedCondition("no physical value meets the requested level")
    repair_lens_wording = False
    if q.kind == "lens" and q.values["image"] == "увеличенного":
        enlarged = feasible.intersect(
            sp.Interval.open(q.values["focus"], 2 * q.values["focus"])
        )
        if enlarged is sp.S.EmptySet:
            repair_lens_wording = True
        else:
            feasible = enlarged
    result = feasible.sup if q.maximum else feasible.inf
    if result.is_Rational is not True or feasible.contains(result) is not sp.S.true:
        raise UnsupportedCondition(
            "the requested extremum must be finite, rational and attained"
        )
    return Analysis(q, feasible, result, repair_lens_wording)


def calculate(context):
    data = common.read(context)
    return data, analyze(parse(data[3]))


def build_context_repair_plan(context):
    data, a = calculate(context)
    condition, ans, solution, _ = data
    result = finish(condition, ans, solution, answer(a.result), fraction_proof.proof(a))
    if a.repair_lens_wording:
        original = _section(_normalized_content(context), "condition")
        corrected = lens_condition.real_image_wording(original["html"])
        result = replace(
            result,
            condition_html=corrected,
            transformations=(
                rewrite(original, "condition", "Условие", corrected),
                *result.transformations,
            ),
        )
    return result
