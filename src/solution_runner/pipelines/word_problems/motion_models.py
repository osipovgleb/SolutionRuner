"""One exact rational time balance for half trips, races and meetings."""

from dataclasses import dataclass, replace

import sympy as sp

from ..calculus.common import answer, real_roots
from ..probability.common import finish
from . import math_common, motion_questions
from .common import UnsupportedCondition

X = sp.Symbol("x", real=True)


@dataclass(frozen=True)
class Balance:
    left: sp.Expr
    right: sp.Expr
    domain: sp.Set
    denominators: tuple
    output: sp.Expr = X


def half_trip(q):
    known, gap = q.values["known"], q.values["gap"]
    if q.kind == "half_gain":
        return Balance(
            1 / X,
            1 / (2 * known) + 1 / (2 * (X + gap)),
            sp.Interval.open(0, sp.oo),
            (X, X + gap),
        )
    lower = max(gap, q.values["minimum"])
    return Balance(
        2 / X, 1 / known + 1 / (X - gap), sp.Interval.open(lower, sp.oo), (X, X - gap)
    )


def different_speeds(q):
    distance, gap = q.values["distance"], q.values["gap"]
    delay = q.durations["delay"].total
    if (
        q.kind in {"race", "return", "water_follow", "water_lake_return"}
        and q.target_fast
    ):
        return Balance(
            distance / X + delay,
            distance / (X - gap),
            sp.Interval.open(gap, sp.oo),
            (X, X - gap),
        )
    return Balance(
        distance / X,
        distance / (X + gap) + delay,
        sp.Interval.open(0, sp.oo),
        (X, X + gap),
    )


def meeting(q):
    v = q.values
    if q.kind == "meeting":
        return Balance(
            (v["first"] + v["second"]) * X,
            v["distance"],
            sp.Interval.open(0, sp.oo),
            (),
        )
    point, distance = v["point"], v["distance"]
    if not 0 < point < distance:
        raise UnsupportedCondition(
            "the meeting point must be strictly between the cities"
        )
    delay = q.durations["delay"].total
    if q.kind == "meeting_point":
        return Balance(delay * X, distance - point, sp.Interval.open(0, sp.oo), ())
    return Balance(
        point / X,
        delay + (distance - point) / v["second"],
        sp.Interval.open(0, sp.oo),
        (X,),
    )


def delayed_point(q):
    v = q.values
    delay = q.durations["delay"].total
    initial_distance = v["first"] * delay
    if initial_distance >= v["distance"]:
        raise UnsupportedCondition(
            "the second car must start before the first reaches the other city"
        )
    return Balance(
        X / v["first"],
        (v["distance"] - X) / v["second"] + delay,
        sp.Interval.open(initial_distance, v["distance"]),
        (),
    )


def trip_time(q):
    delay, meet = (q.durations[key].total for key in ("delay", "meeting"))
    return Balance(
        meet * (1 / X + 1 / (X - delay)),
        sp.Integer(1),
        sp.Interval.open(delay, sp.oo),
        (X, X - delay),
    )


def catch_return(q):
    v = q.values
    delay = q.durations["delay"].total
    if q.kind == "catch_return":
        return Balance(
            (X + delay) / (2 * X + delay),
            v["known"] * X / v["distance"],
            sp.Interval.open(0, sp.oo),
            (2 * X + delay,),
            v["known"] * X,
        )
    catch_time = delay * X / (v["known"] - X)
    return Balance(
        (2 * catch_time + delay) * X,
        v["distance"],
        sp.Interval.open(0, v["known"]),
        (v["known"] - X,),
        v["known"] * catch_time,
    )


def third_cyclist(q):
    first, second = q.values["first"], q.values["second"]
    delay = q.durations["delay"].total
    if q.kind == "third_cyclist":
        speed = second * (X + 1) / X
        return Balance(
            speed * (X + delay),
            first * (X + delay + 2),
            sp.Interval.open(0, sp.oo),
            (X,),
            speed,
        )
    return Balance(
        second / (X - second) + delay,
        2 * first / (X - first),
        sp.Interval.open(max(first, second), sp.oo),
        (X - second, X - first),
    )


def walk_return(q):
    v = q.values
    if v["fast"] <= v["slow"]:
        raise UnsupportedCondition("the returning second walker must be faster")
    return Balance(
        X / v["slow"],
        (2 * v["distance"] - X) / v["fast"],
        sp.Interval.open(0, v["distance"]),
        (),
    )


def downhill(q):
    total, down = (q.durations[key].total for key in ("total", "down"))
    if down >= total:
        raise UnsupportedCondition(
            "positive time for both ascent and descent is required"
        )
    return Balance(
        down * X + (total - down) * (X - q.values["gap"]),
        q.values["distance"],
        sp.Interval.open(q.values["gap"], sp.oo),
        (),
    )


def stopped(q):
    v = q.values
    total = v["reference_distance"] / v["known"]
    delay = q.durations["delay"].total
    if delay >= total:
        raise UnsupportedCondition("the stop must leave positive riding time")
    return Balance(v["distance"] / X + delay, total, sp.Interval.open(0, sp.oo), (X,))


def midpoint(q):
    half = replace(q, values={**q.values, "distance": q.values["distance"] / 2})
    return replace(different_speeds(half), output=X + q.values["gap"])


def water(q):
    from .water_balances import balance

    return balance(q)


BUILDERS = {
    "half_gain": half_trip,
    "half_loss": half_trip,
    "later": different_speeds,
    "return": different_speeds,
    "race": different_speeds,
    "meeting": meeting,
    "meeting_point": meeting,
    "delayed_point": delayed_point,
    "delayed_speed": meeting,
    "trip_time": trip_time,
    "freight": different_speeds,
    "lap_race": different_speeds,
    "catch_return": catch_return,
    "catch_return_speed": catch_return,
    "third_cyclist": third_cyclist,
    "third_cyclist_speed": third_cyclist,
    "walk_return": walk_return,
    "downhill": downhill,
    "stopped": stopped,
    "named_stop": stopped,
    "midpoint": midpoint,
    "water_follow": different_speeds,
    "water_lake_return": different_speeds,
    "water_upgrade": different_speeds,
    "water_current_difference": water,
    "water_boat_difference": water,
    "water_current_stay": water,
    "water_boat_stay": water,
    "water_current_clock": water,
    "water_boat_clock": water,
    "water_distance": water,
    "water_raft": water,
    "water_season_current": water,
    "water_season_boat": water,
}


@dataclass(frozen=True)
class Analysis:
    question: motion_questions.Question
    balance: Balance
    polynomial: sp.Expr
    roots: tuple
    root: sp.Rational
    result: sp.Rational


def analyze(q):
    b = BUILDERS[q.kind](q)
    numerator = sp.together(b.left - b.right).as_numer_denom()[0]
    polynomial = math_common.primitive(numerator, (X,))
    if sp.degree(polynomial, X) not in (1, 2):
        raise UnsupportedCondition("a linear or quadratic time balance is required")
    roots = tuple(sorted(real_roots(polynomial, X), reverse=True))
    valid = [
        r
        for r in roots
        if b.domain.contains(r) is sp.true
        and all(d.subs(X, r) != 0 for d in b.denominators)
    ]
    if len(valid) != 1 or valid[0].is_Rational is not True:
        raise UnsupportedCondition(
            "one exact rational physical root is required without rounding"
        )
    root = valid[0]
    if sp.simplify((b.left - b.right).subs(X, root)) != 0:
        raise UnsupportedCondition("the root must satisfy the original time balance")
    if (
        q.kind == "trip_time"
        and q.durations["meeting"].total >= root - q.durations["delay"].total
    ):
        raise UnsupportedCondition(
            "the meeting must occur before either traveler finishes"
        )
    if q.kind == "lap_race" and q.durations["lap_time"].total >= q.values[
        "distance"
    ] / (root + q.values["gap"]):
        raise UnsupportedCondition("the first lap catch must precede the finish")
    result = sp.cancel(b.output.subs(X, root))
    if result.is_Rational is not True or result <= 0:
        raise UnsupportedCondition(
            "one positive exact rational requested quantity is required"
        )
    return Analysis(q, b, polynomial, roots, root, result)


def alternate(q):
    kind = {
        "catch_return": "catch_return_speed",
        "third_cyclist": "third_cyclist_speed",
    }[q.kind]
    return analyze(replace(q, kind=kind))


def calculate(context):
    data = math_common.read(context)
    return data, analyze(motion_questions.parse(data[3]))


def build_context_repair_plan(context):
    from .motion_proof import proof

    data, analysis = calculate(context)
    condition, ans, solution, _ = data
    return finish(condition, ans, solution, answer(analysis.result), proof(analysis))
