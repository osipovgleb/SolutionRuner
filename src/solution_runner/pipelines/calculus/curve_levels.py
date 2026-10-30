"""Count horizontal levels by monotone arcs; locate SVG marks independently."""

from fractions import Fraction
from itertools import pairwise

import numpy as np

from ..probability.common import UnsupportedCondition


def ordinate_sign(node, level):
    level = Fraction(str(level))
    if "y" in node:
        value = Fraction(node["y"])
        return (value > level) - (value < level)
    lower, upper = map(Fraction, node["y_bounds"])
    if lower >= upper or lower <= level <= upper:
        raise UnsupportedCondition(
            "the source does not resolve a level near a curve vertex"
        )
    return -1 if upper < level else 1


def count(nodes, level):
    if len(nodes) < 2 or any(a["svg"][0] >= b["svg"][0] for a, b in pairwise(nodes)):
        raise UnsupportedCondition(
            "ordered endpoints and all monotone-arc vertices are required"
        )
    signs = [ordinate_sign(node, level) for node in nodes]
    if any(a == b == 0 for a, b in pairwise(signs)):
        raise UnsupportedCondition("a constant level arc has infinitely many solutions")
    vertices = sum(
        sign == 0 and not node.get("endpoint", False)
        for node, sign in zip(nodes, signs, strict=True)
    )
    arcs = sum(a * b < 0 for a, b in pairwise(signs))
    return vertices + arcs


def svg_intersections(entry, level):
    _ox, oy = entry["svg_origin"]
    unit = entry["svg_unit"]
    target = oy - float(level) * unit
    points = []
    for control in entry["curve_segments"]:
        control = np.asarray(control, dtype=float)
        if control.shape != (4, 2) or not np.isfinite(control).all():
            raise UnsupportedCondition("four finite cubic control points are required")
        a, b, c, d = control[:, 1]
        coefficients = np.trim_zeros(
            np.array(
                [
                    -a + 3 * b - 3 * c + d,
                    3 * a - 6 * b + 3 * c,
                    -3 * a + 3 * b,
                    a - target,
                ]
            ),
            "f",
        )
        if len(coefficients) == 0:
            raise UnsupportedCondition("the SVG contains a horizontal level segment")
        for root in np.roots(coefficients):
            if abs(root.imag) > 1e-7 or not -1e-8 <= root.real <= 1 + 1e-8:
                continue
            t = float(np.clip(root.real, 0, 1))
            weights = np.array(
                [(1 - t) ** 3, 3 * t * (1 - t) ** 2, 3 * t * t * (1 - t), t**3]
            )
            x = float(weights @ control[:, 0])
            points.append((x, target))
    return points


def distinct_points(points, left, right):
    points = sorted(p for p in points if left + 0.05 < p[0] < right - 0.05)
    unique = []
    for p in points:
        if not unique or p[0] - unique[-1][0] > 0.5:
            unique.append(p)
    return unique


def intersections(entry, level):
    points = svg_intersections(entry, level)
    unit = entry["svg_unit"]
    target = entry["svg_origin"][1] - float(level) * unit
    # Exact grid vertices override subpixel drawing errors at a tangent level.
    for node in entry["curve_nodes"]:
        if ordinate_sign(node, level) == 0:
            x = node["svg"][0]
            points = [p for p in points if abs(p[0] - x) > unit * 0.15]
            if not node.get("endpoint", False):
                points.append((x, target))
    left, right = entry["curve_nodes"][0]["svg"][0], entry["curve_nodes"][-1]["svg"][0]
    unique = distinct_points(points, left, right)
    if len(unique) != count(entry["curve_nodes"], level):
        raise UnsupportedCondition(
            "the SVG intersections and monotone-arc count disagree"
        )
    return unique
