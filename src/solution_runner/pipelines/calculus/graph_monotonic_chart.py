"""Exact and bounded sign-chart boundaries, independent of answer formatting."""

from fractions import Fraction
from itertools import pairwise

from ..probability.common import UnsupportedCondition, line
from .common import answer
from .graph_extrema import derivative_extrema


def bounds(point):
    if "x" in point:
        value = Fraction(point["x"])
        return value, value
    return tuple(map(Fraction, point["x_bounds"]))


def compare(point, x):
    """Compare a reviewed exact/bounded abscissa with an exact query boundary."""
    lo, hi = bounds(point)
    if lo == hi:
        return (lo > x) - (lo < x)
    opened = point.get("x_bounds_open", [False, False])
    if x < lo or x == lo and opened[0]:
        return 1
    if x > hi or x == hi and opened[1]:
        return -1
    raise UnsupportedCondition("the graph does not resolve this interval boundary")


def chart(entry, question):
    if (
        entry.get("curve_name") != ("derivative" if question.derivative else "f")
        or list(map(Fraction, entry["monotonic_domain"]))
        != [question.domain.lower, question.domain.upper]
        or entry["domain_closed"]
        != [question.domain.lower_closed, question.domain.upper_closed]
    ):
        raise UnsupportedCondition(
            "the audited graph role and domain must match the question"
        )
    if (
        question.domain.lower_closed or question.domain.upper_closed
    ) and not question.continuous:
        raise UnsupportedCondition(
            "continuity is required at included domain endpoints"
        )
    points = entry["zero_points"] if question.derivative else entry["monotonic_points"]
    if question.derivative and entry.get("curve_segments"):
        derivative_extrema(
            {**entry, "zero_points": [p for p in points if p.get("defined", True)]}
        )
    previous = entry["initial_sign"]
    if previous not in [-1, 1]:
        raise UnsupportedCondition("a nonzero initial sign is required")
    boundary = {"x": question.domain.lower}
    nodes = [(boundary, question.domain.lower_closed)]
    for point in points:
        if (
            point["left_sign"] != previous
            or point["right_sign"] not in [-1, 1]
            or bounds(boundary)[1] > bounds(point)[0]
            or compare(point, question.domain.lower) <= 0
            or compare(point, question.domain.upper) >= 0
        ):
            raise UnsupportedCondition("a complete ordered sign chart is required")
        previous = point["right_sign"]
        closed = question.operation != "count" and (
            point.get("defined", True) or question.continuous
        )
        nodes.append((point, closed))
        boundary = point
    nodes.append(({"x": question.domain.upper}, question.domain.upper_closed))
    bands = []
    sign = entry["initial_sign"]
    for start, end in pairwise(nodes):
        band = (start[0], end[0], start[1], end[1], sign)
        if bands and bands[-1][4] == sign and start[1]:
            first = bands.pop()
            band = (first[0], end[0], first[2], end[1], sign)
        bands.append(band)
        sign = end[0].get("right_sign", sign)
    return bands


def integers(bands, domain):
    result = []
    for n in range(domain.lower.__ceil__(), domain.upper.__floor__() + 1):
        for left, right, lc, rc, _ in bands:
            a, b = compare(left, n), compare(right, n)
            if (a < 0 or a == 0 and lc) and (b > 0 or b == 0 and rc):
                result.append(n)
                break
    return result


def band_latex(band, labels):
    left, right, lc, rc, _ = band
    return (
        ("[" if lc else "(")
        + labels[id(left)]
        + ";"
        + labels[id(right)]
        + ("]" if rc else ")")
    )


def describe(bands):
    labels = {}
    constraints = ""
    for band in bands:
        for point in band[:2]:
            if id(point) in labels:
                continue
            if "x" in point:
                labels[id(point)] = answer(point["x"]).replace(",", "{,}")
            else:
                label = rf"a_{{{1 + sum('a_' in s for s in labels.values())}}}"
                labels[id(point)] = label
                lo, hi = bounds(point)
                opened = point.get("x_bounds_open", [False, False])
                constraints += line(
                    answer(lo)
                    + ("<" if opened[0] else r"\leq")
                    + label
                    + ("<" if opened[1] else r"\leq")
                    + answer(hi)
                )
    return labels, constraints


def global_point(question, bands):
    span = question.span
    if (
        span.lower < question.domain.lower
        or span.upper > question.domain.upper
        or span.lower == question.domain.lower
        and span.lower_closed
        and not question.domain.lower_closed
        or span.upper == question.domain.upper
        and span.upper_closed
        and not question.domain.upper_closed
    ):
        raise UnsupportedCondition(
            "the requested interval lies outside the function domain"
        )
    active = [
        b
        for b in bands
        if compare(b[0], span.upper) < 0 and compare(b[1], span.lower) > 0
    ]
    maximum = question.target == "наибольшее"
    if len(active) == 1:
        use_right = (active[0][4] > 0) == maximum
        closed = span.upper_closed if use_right else span.lower_closed
        if not closed:
            raise UnsupportedCondition("the extremal endpoint is not included")
        return span.upper if use_right else span.lower
    wanted = [1, -1] if maximum else [-1, 1]
    if len(active) == 2 and [b[4] for b in active] == wanted:
        left = active[0][1]
        if "x" in left:
            return Fraction(left["x"])
    raise UnsupportedCondition(
        "global extrema require comparison of all remaining candidates"
    )
