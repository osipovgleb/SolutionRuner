"""Use existing root and interval certificates for quadratic-exponent preimages."""

from dataclasses import dataclass

import sympy as sp

from ..probability.common import UnsupportedCondition
from .exam_exponential import back_substitute
from .exam_scalar import enclose
from .exponential_inequality_quadratic import (
    PositivePower,
    normalize_powers,
    power_stage,
    read_power_sum,
)
from .exponential_inequality_quadratic_labels import root_text
from .rational_inequality import interval_signs
from .rational_inequality_parser import polynomial


@dataclass(frozen=True)
class Condition:
    bound: sp.Expr
    operator: str
    value: sp.Expr
    points: tuple
    solution: object


def condition(base, exponent, bound, operator):
    _, back = back_substitute(base, exponent, (bound,), quadratic_logs=True)
    if len(back) != 1:
        raise UnsupportedCondition("one positive logarithmic level is required")
    _, value, points = back[0]
    solution = (
        sp.FiniteSet(*points)
        if operator == "="
        else interval_signs(sp.expand(exponent - value), points, operator, ())[1]
    )
    return Condition(bound, operator, value, points, solution)


@dataclass(frozen=True)
class Branch:
    values: object
    conditions: tuple
    solution: object


def branch(base, exponent, values):
    if isinstance(values, sp.FiniteSet):
        conditions = tuple(condition(base, exponent, t, "=") for t in values)
        solution = sp.Union(*(c.solution for c in conditions))
    elif isinstance(values, sp.Interval):
        conditions = []
        if values.start > 0:
            conditions.append(
                condition(
                    base, exponent, values.start, ">" if values.left_open else ">="
                )
            )
        if values.end != sp.oo:
            conditions.append(
                condition(
                    base, exponent, values.end, "<" if values.right_open else "<="
                )
            )
        solution = (
            sp.Intersection(*(c.solution for c in conditions))
            if conditions
            else sp.S.Reals
        )
    else:
        raise UnsupportedCondition(
            "the positive-power branches must be points or intervals"
        )
    return Branch(values, tuple(conditions), solution)


def branches(base, exponent, solution):
    if solution == sp.EmptySet:
        return ()
    parts = solution.args if isinstance(solution, sp.Union) else (solution,)
    return tuple(branch(base, exponent, part) for part in parts)


@dataclass(frozen=True, kw_only=True)
class QuadraticPower(PositivePower):
    power_range: object
    reachable_solution: object
    branches: tuple
    reachable_branches: tuple

    def endpoint(self, value):
        return root_text(self, value)


def power_range(base, exponent):
    p = polynomial(exponent)
    if p.degree() != 2 or any(c.is_Rational is not True for c in p.all_coeffs()):
        raise UnsupportedCondition("a rational quadratic exponent is required")
    vertex = -p.nth(1) / (2 * p.nth(2))
    extreme = p.eval(vertex)
    if abs(extreme) > 40 or extreme.q > 2:
        raise UnsupportedCondition(
            "the quadratic range limit exceeds the reviewed scalar bounds"
        )
    limit = base**extreme
    if any(max(abs(n.p), n.q) > 10**12 for n in limit.atoms(sp.Rational)):
        raise UnsupportedCondition(
            "the positive range limit exceeds exact arithmetic bounds"
        )
    enclose(limit, 32)
    return sp.Interval(limit, sp.oo) if p.LC() > 0 else sp.Interval.Lopen(0, limit)


def analyze(formula):
    operator, original, powers, constant = read_power_sum(formula)
    base, exponent, coefficients = normalize_powers(
        powers, constant, exponent_degree=2, preserve_shift=True
    )
    multiply_degree, stage = power_stage(coefficients, operator)
    positive = sp.Intersection(stage.solution, sp.Interval.open(0, sp.oo))
    value_range = power_range(base, exponent)
    reachable = sp.Intersection(positive, value_range)
    parts = branches(base, exponent, positive)
    reachable_parts = branches(base, exponent, reachable)
    _, back = back_substitute(base, exponent, stage.zeros, quadratic_logs=True)
    solution = sp.Union(*(b.solution for b in parts))
    return QuadraticPower(
        formula,
        operator,
        original,
        powers,
        constant,
        base,
        exponent,
        tuple(sorted(coefficients.items())),
        multiply_degree,
        stage,
        positive,
        tuple(back),
        solution,
        power_range=value_range,
        reachable_solution=reachable,
        branches=parts,
        reachable_branches=reachable_parts,
    )
