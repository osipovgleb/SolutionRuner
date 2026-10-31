"""Additive work rates with the common exact time-balance solver."""

import sympy as sp

from .common import UnsupportedCondition
from .time_balance import Balance, X


def summed(q):
    v = q.values
    times = [v[key] for key in ("t1", "t2", "t3") if key in v]
    amount = v.get("volume", sp.Integer(1))
    rate = sum(amount / t for t in times)
    return Balance(
        rate * X, v.get("target", sp.Integer(1)), sp.Interval.open(0, sp.oo), ()
    )


def equal_join(q):
    solo, delay = q.values["solo"], q.values["delay"]
    if delay >= solo:
        raise UnsupportedCondition("the second worker must join before completion")
    return Balance(
        delay / solo + 2 * (X - delay) / solo,
        sp.Integer(1),
        sp.Interval.open(delay, solo),
        (),
    )


def known(q):
    joint, alone = q.values["joint"], q.values["known"]
    if alone <= joint:
        raise UnsupportedCondition("the known solo time must exceed the joint time")
    return Balance(1 / X + 1 / alone, 1 / joint, sp.Interval.open(joint, sp.oo), (X,))


def gap(q):
    joint, difference = q.values["joint"], q.values["gap"]
    if q.kind == "work_gap_filter":
        return Balance(
            1 / X + 1 / (X - difference),
            1 / joint,
            sp.Interval.open(max(difference, joint), sp.oo),
            (X, X - difference),
            X - difference,
        )
    return Balance(
        1 / X + 1 / (X + difference),
        1 / joint,
        sp.Interval.open(joint, sp.oo),
        (X, X + difference),
    )


def ratio_workers(q):
    v = q.values
    fraction = v["span1"] / v["span2"]
    return Balance(
        1 / X + fraction / X, 1 / v["joint"], sp.Interval.open(v["joint"], sp.oo), (X,)
    )


def apprentice(q):
    v = q.values
    if v["ratio"] <= 1 or v["ratio"] * v["apprentice"] <= v["master"]:
        raise UnsupportedCondition(
            "the master's later start must leave a positive time gap"
        )
    factor = v["ratio"] * v["apprentice"] / v["master"]
    return Balance(
        (v["ratio"] + 1) * X / v["master"],
        sp.Integer(1),
        sp.Interval.open(0, v["master"]),
        (),
        (factor - 1) * X,
    )


BUILDERS = {
    "work_equal_join": equal_join,
    "work_sum_two": summed,
    "work_sum_three": summed,
    "work_measured_sum": summed,
    "work_known_girl": known,
    "work_known_pipe": known,
    "work_gap_pipes": gap,
    "work_gap_filter": gap,
    "work_gap_printer": gap,
    "work_ratio_workers": ratio_workers,
    "work_apprentice": apprentice,
}
