"""Exact regular-prism vertices, lengths, angles and label-preserving body isometries."""

import itertools
import re

import sympy as sp

from ..core.errors import ContentPlanError
from .box_coordinates import VERTICES

VERTEX = r"[A-F](?:_1)?"


def names(raw, count):
    if re.fullmatch(rf"(?:{VERTEX}){{{count}}}", raw) is None:
        raise ContentPlanError("canonical distinct prism vertices are required")
    result = tuple(re.findall(VERTEX, raw))
    if len(set(result)) != count:
        raise ContentPlanError("the prism points must be distinct")
    return result


def frame(body, height=sp.S.One):
    if body not in {"cube", "square", "triangle", "hexagon"}:
        raise ContentPlanError("the regular prism body needs review")
    if body in {"cube", "square"}:
        return {n: sp.Matrix((x, y, z * height)) for n, (x, y, z) in VERTICES.items()}
    base = (
        ((0, 0), (1, 0), (sp.Rational(1, 2), sp.sqrt(3) / 2))
        if body == "triangle"
        else tuple((sp.cos(i * sp.pi / 3), sp.sin(i * sp.pi / 3)) for i in range(6))
    )
    return {
        chr(65 + i) + ("_1" if level else ""): sp.Matrix((x, y, level * height))
        for level in (0, 1)
        for i, (x, y) in enumerate(base)
    }


def vector(points, segment):
    a, b = names(segment, 2)
    if a not in points or b not in points:
        raise ContentPlanError("a vertex lies outside the named prism")
    return points[b] - points[a]


def squared(points, segment):
    v = vector(points, segment)
    return sp.simplify(v.dot(v))


def cosine(u, v, *, lines=False):
    product = sp.simplify(u.dot(v))
    denominator = sp.sqrt(u.dot(u) * v.dot(v))
    if denominator == 0:
        raise ContentPlanError("nonzero rays or lines are required")
    return sp.simplify((sp.Abs(product) if lines else product) / denominator)


def degrees(c):
    table = {
        sp.S.Zero: 90,
        sp.S.One: 0,
        -sp.S.One: 180,
        sp.Rational(1, 2): 60,
        -sp.Rational(1, 2): 120,
        sp.sqrt(2) / 2: 45,
        -sp.sqrt(2) / 2: 135,
        sp.sqrt(3) / 2: 30,
        -sp.sqrt(3) / 2: 150,
    }
    if c not in table:
        raise ContentPlanError("the prism angle needs a reviewed exact degree value")
    return sp.Integer(table[c])


def isometries(body):
    if body == "cube":
        reverse = {tuple(p): n for n, p in VERTICES.items()}
        for order in itertools.permutations(range(3)):
            for flips in itertools.product((0, 1), repeat=3):
                yield {
                    n: reverse[
                        tuple(
                            (1 - p[order[i]]) if flips[i] else p[order[i]]
                            for i in range(3)
                        )
                    ]
                    for n, p in VERTICES.items()
                }
        return
    size = {"triangle": 3, "hexagon": 6, "square": 4}[body]
    for shift, direction, flip in itertools.product(range(size), (-1, 1), (0, 1)):
        yield {
            chr(65 + i) + ("_1" if layer else ""): chr(
                65 + (shift + direction * i) % size
            )
            + ("_1" if layer ^ flip else "")
            for layer in (0, 1)
            for i in range(size)
        }
