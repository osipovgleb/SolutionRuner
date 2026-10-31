"""Paired rates, integer counts and related work equations share one solver."""

import sympy as sp

from .common import UnsupportedCondition
from .time_balance import Balance, X


def pair_rates(q):
    rates = tuple(1 / q.values[k] for k in ("t12", "t23", "t13"))
    total = sum(rates) / 2
    if any(total - r <= 0 for r in rates):
        raise UnsupportedCondition(
            "each individual in the pair data must have a positive rate"
        )
    return total, rates


def pairs(q):
    total, _ = pair_rates(q)
    return Balance(total * X, sp.Integer(1), sp.Interval.open(0, sp.oo), ())


def test_count(q):
    v = q.values
    if v["rate1"] >= v["rate2"]:
        raise UnsupportedCondition(
            "the participant finishing later must have the lower rate"
        )
    return Balance(X / v["rate1"] - X / v["rate2"], v["delay"], sp.S.Naturals, ())


def tile(q):
    amount, increase, saved = (q.values[k] for k in ("amount", "gap", "delay"))
    if q.kind == "work_tile":
        return Balance(
            (increase * X / saved - increase) * X,
            amount,
            sp.Interval.open(saved, sp.oo),
            (X,),
            amount / X,
        )
    domain = sp.Interval.open(0, amount / saved)
    if q.kind == "work_tile_product":
        return Balance((X + increase) * (amount / X - saved), amount, domain, (X,))
    return Balance(
        amount / X - amount / (X + increase), saved, domain, (X, X + increase)
    )


def crews(q):
    v = q.values
    first, second, transfer = (v[k] for k in ("first", "second", "transfer"))
    if (
        any(value.is_Integer is not True for value in (first, second, transfer))
        or not 0 < transfer < second
        or first >= second
        or first + transfer <= second - transfer
    ):
        raise UnsupportedCondition(
            "positive integer crews must allow the initially smaller crew to catch up after transfer"
        )
    return Balance(
        first * v["initial"] + (first + transfer) * X,
        second * v["initial"] + (second - transfer) * X,
        sp.Interval.open(0, sp.oo),
        (),
        X + v["include_initial"] * v["initial"],
    )


def integer_solver(q):
    v = q.values
    if any(v[k].is_Integer is not True for k in ("gap", "joint_tasks", "target")):
        raise UnsupportedCondition(
            "integer hourly task counts and integer job amounts are required"
        )
    domain = sp.Intersection(sp.S.Integers, sp.Interval(1, sp.oo))
    return Balance(
        v["joint_tasks"] / (X + v["gap"]) - v["joint_tasks"] / (2 * X + v["gap"]),
        v["delay"],
        domain,
        (X + v["gap"], 2 * X + v["gap"], X),
        v["target"] / X,
    )


BUILDERS = {
    "work_pairs_boys": pairs,
    "work_pairs_pumps": pairs,
    "work_test_count": test_count,
    "work_tile": tile,
    "work_tile_product": tile,
    "work_tile_difference": tile,
    "work_crews": crews,
    "work_integer_solver": integer_solver,
}
