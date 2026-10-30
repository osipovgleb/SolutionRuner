"""Exact polynomial boundary solutions restricted to the physical stage."""

from dataclasses import dataclass

import sympy as sp

from ..calculus.common import answer, real_roots
from ..probability import solution_diagrams as diagrams
from ..probability.common import UnsupportedCondition, finish
from . import bridge_assets, bridge_proof, physical_proof
from .physical_questions import Question, parse


@dataclass(frozen=True)
class Analysis:
    question: Question
    roots: tuple
    selected: tuple
    result: sp.Expr
    physical_end: sp.Expr | None = None
    interval: tuple | None = None
    measurements: tuple = ()


def coefficients(question):
    p = sp.Poly(question.expression, question.variable)
    if p.degree() != 2 or any(c.is_Rational is not True for c in p.all_coeffs()):
        raise UnsupportedCondition("an exact quadratic physical law is required")
    return p.nth(2), p.nth(1), p.nth(0)


def validate_parameters(q, a, b, c):
    values = q.values
    expected = None
    if q.kind in ["tank_empty", "heater"]:
        expected = (values["a"], values["b"], values["initial"])
    elif q.kind in ["braking", "coverage"]:
        if values["speed"] <= 0 or values["a"] <= 0:
            raise UnsupportedCondition(
                "positive speed and acceleration magnitude are required"
            )
        expected = (
            (-1 if q.kind == "braking" else 1) * values["a"] / 2,
            values["speed"],
            0,
        )
    elif q.kind == "winding":
        if values["omega"] <= 0 or values["beta"] <= 0:
            raise UnsupportedCondition(
                "positive angular speed and acceleration are required"
            )
        expected = (values["beta"] / 2, values["omega"], 0)
    elif q.kind == "barrier":
        if values["wall"] < 0 or values["clearance"] < 0:
            raise UnsupportedCondition(
                "nonnegative wall height and clearance are required"
            )
        expected = (values["a"], values["b"], 0)
    elif q.kind == "thermal_duration" and c != values["initial"]:
        raise UnsupportedCondition(
            "the law must reproduce the stated initial temperature"
        )
    if expected is not None and (a, b, c) != expected:
        raise UnsupportedCondition(
            "the formula contradicts its stated physical parameters"
        )


def well(q, a, b, c):
    before, change = q.values["before"], q.values["change"]
    if a <= 0 or b != 0 or c != 0 or before <= 0 or not 0 <= change <= before:
        raise UnsupportedCondition(
            "falling-time measurements must be nonnegative and consistent"
        )
    after = before - change
    initial = q.expression.subs(q.variable, before)
    final = q.expression.subs(q.variable, after)
    return Analysis(
        q,
        (),
        (),
        sp.simplify(initial - final),
        measurements=(before, after, initial, final),
    )


def duration(q, a, b, c, roots):
    if a >= 0 or b <= 0 or c < 0 or q.target < 0:
        raise UnsupportedCondition(
            "a rising then falling nonnegative initial physical law is required"
        )
    if not roots or roots[-1] < 0:
        return Analysis(q, roots, (), sp.Integer(0))
    start, end = max(sp.Integer(0), roots[0]), roots[-1]
    return Analysis(
        q,
        roots,
        tuple(x for x in roots if x >= 0),
        sp.simplify(end - start),
        interval=(start, end),
    )


def draining(q, a, b, c, roots):
    if a <= 0 or b >= 0 or c <= 0 or q.target < 0 or q.target >= c:
        raise UnsupportedCondition(
            "the tank must start above its target and be draining"
        )
    empty = [r for r in real_roots(q.expression, q.variable) if r >= 0]
    if not empty:
        raise UnsupportedCondition("the tank law must reach empty before reversing")
    stop = min(empty)
    if q.expression.diff(q.variable).subs(q.variable, stop) > 0:
        raise UnsupportedCondition("the tank must not reverse before emptying")
    valid = tuple(r for r in roots if 0 <= r <= stop)
    if len(valid) != 1:
        raise UnsupportedCondition("exactly one time in the draining stage is required")
    return Analysis(q, roots, valid, valid[0], physical_end=stop)


def bounded(q, a, b, c, roots):
    if q.kind == "braking":
        if a >= 0 or b <= 0 or c != 0 or q.target < 0:
            raise UnsupportedCondition(
                "a positive initial speed and a braking stage are required"
            )
        stop = -b / (2 * a)
        valid = tuple(r for r in roots if 0 <= r <= stop)
        result = valid[0] if len(valid) == 1 else None
    elif q.kind == "heater":
        if a >= 0 or b <= 0 or c <= 0 or q.target < c:
            raise UnsupportedCondition("the heater must start safe and warm up")
        stop = -b / (2 * a)
        if q.expression.subs(q.variable, stop) <= q.target:
            raise UnsupportedCondition("there is no later unsafe temperature crossing")
        valid = tuple(r for r in roots if 0 <= r < stop)
        result = valid[0] if len(valid) == 1 else None
    elif q.kind == "barrier":
        if a >= 0 or b <= 0 or c != 0 or q.target <= 0:
            raise UnsupportedCondition("a positive projectile clearance is required")
        stop = -b / a
        valid = tuple(r for r in roots if 0 <= r <= stop)
        result = max(valid) if valid else None
    else:
        if a <= 0 or b <= 0 or c != 0 or q.target < 0:
            raise UnsupportedCondition("a monotonic accelerating stage is required")
        stop = None
        valid = tuple(r for r in roots if r >= 0)
        result = valid[0] if len(valid) == 1 else None
    if result is None:
        raise UnsupportedCondition(
            "the physical constraints do not determine a unique requested boundary"
        )
    return Analysis(q, roots, valid, sp.simplify(result * q.scale), physical_end=stop)


def analyze(question):
    a, b, c = coefficients(question)
    validate_parameters(question, a, b, c)
    if question.kind == "bridge":
        return bridge(question, a, b, c)
    if question.kind == "well":
        return well(question, a, b, c)
    roots = tuple(real_roots(question.expression - question.target, question.variable))
    if question.kind in ["duration", "thermal_duration"]:
        return duration(question, a, b, c, roots)
    if question.kind in ["tank_empty", "tank_fraction"]:
        return draining(question, a, b, c, roots)
    return bounded(question, a, b, c, roots)


def bridge(q, a, b, c):
    distance = q.values["distance"]
    if a <= 0 or b >= 0 or c <= 0 or not 0 <= distance <= -b / a:
        raise UnsupportedCondition(
            "a sagging bridge span and a point between its pylons are required"
        )
    result = q.expression.subs(q.variable, distance)
    if result < 0:
        raise UnsupportedCondition("the requested cable length cannot be negative")
    vertex = -b / (2 * a)
    return Analysis(
        q,
        (),
        (),
        result,
        physical_end=-b / a,
        measurements=(vertex, q.expression.subs(q.variable, vertex)),
    )


def read_question(context):
    data = bridge_assets.read(context)
    q = parse(data[3])
    if (q.kind == "bridge") != bool(context["normalized_content"].get("assets")):
        raise UnsupportedCondition(
            "only the bridge law may use the required bridge figures"
        )
    return data, q


def calculate(context):
    data, q = read_question(context)
    return data, analyze(q)


def required_assets(context):
    _, q = read_question(context)
    return bridge_assets.required_asset() if q.kind == "bridge" else ()


def build_context_repair_plan(context):
    data, analysis = calculate(context)
    condition, ans, solution, _ = data
    if analysis.question.kind == "bridge":
        image, key, changes = bridge_assets.image(context)
        return diagrams.repair(
            condition,
            ans,
            solution,
            answer(analysis.result),
            bridge_proof.proof(analysis) + image,
            (key,),
            changes,
        )
    html = physical_proof.proof(analysis)
    return finish(condition, ans, solution, answer(analysis.result), html)
