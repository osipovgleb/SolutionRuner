"""Water trip equations reuse the exact linear/quadratic balance solver."""

import sympy as sp

from .common import UnsupportedCondition
from .motion_models import Balance, X

CURRENT_KINDS = {
    "water_current_difference",
    "water_current_stay",
    "water_current_clock",
}


def seasonal_factors(q):
    spring, summer = (q.values[k] for k in ("spring_ratio", "summer_ratio"))
    if not spring > summer > 1:
        raise UnsupportedCondition(
            "the spring ratio must exceed the summer ratio, both greater than one"
        )
    return (spring + 1) / (spring - 1), (summer + 1) / (summer - 1)


def season(q):
    a, b = seasonal_factors(q)
    gap = q.values["gap"]
    output = a * X if q.kind == "water_season_boat" else X
    return Balance(a * X, b * (X - gap), sp.Interval.open(gap, sp.oo), (), output)


def distance(q):
    boat, current = q.values["boat"], q.values["current"]
    if boat <= current:
        raise UnsupportedCondition("the boat must be faster than the current")
    return Balance(
        X / (boat - current) + X / (boat + current),
        q.durations["moving"].total,
        sp.Interval.open(0, sp.oo),
        (boat - current, boat + current),
        2 * X,
    )


def balance(q):
    if q.kind in {"water_season_current", "water_season_boat"}:
        return season(q)
    if q.kind == "water_distance":
        return distance(q)
    unknown_current = q.kind in CURRENT_KINDS
    boat, current = (
        (q.values["known"], X) if unknown_current else (X, q.values["known"])
    )
    up, down = (
        q.values["distance"] / (boat - current),
        q.values["distance"] / (boat + current),
    )
    if q.kind.endswith("_difference"):
        left, right = up - down, q.durations["delay"].total
    elif q.kind == "water_raft":
        left = up + down
        right = q.values["raft_distance"] / current - q.durations["delay"].total
        if right <= 0:
            raise UnsupportedCondition(
                "the yacht must have positive sailing time after its delayed start"
            )
    else:
        left, right = up + down, q.durations["moving"].total
    domain = (
        sp.Interval.open(0, boat)
        if unknown_current
        else sp.Interval.open(current, sp.oo)
    )
    return Balance(left, right, domain, (boat - current, boat + current))
