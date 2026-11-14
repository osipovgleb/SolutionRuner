"""Exact rational inverse comparisons with the uncancelled source domain."""

from dataclasses import dataclass, replace

import sympy as sp

from ..probability.common import UnsupportedCondition
from .rational_inequality import analyze, interval_signs
from .rational_inequality_algebraic_methods import original_orientation
from .rational_inequality_parser import X, checked
from .rational_inequality_proof import RELATION
from .rational_inequality_roots import ordered, real_roots


def excluded_points(denominators):
    points = set()
    for denominator in denominators:
        if denominator == 0:
            raise UnsupportedCondition("an original denominator is identically zero")
        numerator, denominator = sp.fraction(sp.cancel(checked(denominator)))
        for value in (numerator, denominator):
            points.update(real_roots(value))
    return ordered(points)


def comparison(value, operator, *, denominators=()):
    value = sp.cancel(checked(value))
    if operator == "=":
        value = checked(value**2)
        operator = "<="
    stage = original_orientation(analyze(sp.latex(value) + RELATION[operator] + "0"))
    if not denominators:
        return stage
    poles = ordered(set(stage.poles) | set(excluded_points(denominators)))
    points = ordered(set(stage.zeros) | set(poles))
    signs, solution = interval_signs(
        stage.expression, points, stage.sign_operator, poles
    )
    denominator = sp.fraction(sp.cancel(stage.expression))[1]
    holes = tuple(p for p in poles if sp.simplify(denominator.subs(X, p)) != 0)
    return replace(
        stage, poles=poles, points=points, signs=signs, solution=solution, holes=holes
    )


@dataclass(frozen=True)
class Level:
    bound: sp.Expr
    operator: str
    stage: object


@dataclass(frozen=True)
class Branch:
    values: object
    conditions: tuple
    domain: object
    solution: object


def bounds(part):
    if isinstance(part, sp.FiniteSet) and len(part) == 1:
        return ((next(iter(part)), "="),)
    if isinstance(part, sp.Interval):
        rows = []
        if part.start != -sp.oo:
            rows.append((part.start, ">" if part.left_open else ">="))
        if part.end != sp.oo:
            rows.append((part.end, "<" if part.right_open else "<="))
        return tuple(rows)
    raise UnsupportedCondition("inverse substitution needs exact points or intervals")


def branches(values, domain, inverse, *, positive=False):
    if values == sp.EmptySet or domain == sp.EmptySet:
        return ()
    if values == sp.S.Reals:
        values = sp.Interval.open(-sp.oo, sp.oo)
    parts = values.args if isinstance(values, sp.Union) else (values,)
    parts = tuple(
        singleton
        for part in parts
        for singleton in (
            tuple(sp.FiniteSet(p) for p in part)
            if isinstance(part, sp.FiniteSet)
            else (part,)
        )
    )
    result = []
    for part in parts:
        conditions = tuple(
            Level(t, op, inverse(t, op))
            for t, op in bounds(part)
            if not (positive and t == 0 and op == ">")
        )
        solution = sp.Intersection(domain, *(c.stage.solution for c in conditions))
        result.append(Branch(part, conditions, domain, solution))
    return tuple(result)
