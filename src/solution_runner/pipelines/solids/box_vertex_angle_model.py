"""Prove acute isosceles angles from actual rectangular-box vertex triples."""

import itertools
import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from . import box_coordinates as c
from .box_geometry_input import assignments, text

ANGLE = rf"(?:{c.VERTEX}){{3}}"
IDENTIFIERS = tuple("".join(v) for v in itertools.permutations(c.VERTICES, 3))
SUFFIX = r"(?:Дайте ответ|Ответ дайте) в градусах\."
FIRST = rf"Найдите угол\s+({ANGLE})\s+прямоугольного параллелепипеда,\s*для которого\s+(.+?)\s*\.\s*{SUFFIX}"
SECOND = rf"[ВB] прямоугольном параллелепипеде\s+{c.HEADER}\s*известно, что\s+(.+?)\s*\.\s*Найдите угол\s+({ANGLE})\s*\.\s*{SUFFIX}"


@dataclass(frozen=True)
class BoxVertexAngle:
    given: tuple[tuple[str, sp.Expr], ...]
    requested: str
    vertices: tuple[str, ...]
    squares: tuple[sp.Expr, ...]
    right: str
    legs: tuple[str, str]
    answer: sp.Expr


def read_question(html, source=None):
    condition = text(html, source, extra_identifiers=IDENTIFIERS)
    match = re.fullmatch(FIRST, condition)
    if match:
        requested, raw = match.groups()
    else:
        match = re.fullmatch(SECOND, condition)
        if match is None:
            raise ContentPlanError("one complete box vertex-angle question is required")
        raw, requested = match.groups()
    points = tuple(re.findall(c.VERTEX, requested))
    if len(set(points)) != 3:
        raise ContentPlanError("three distinct angle vertices are required")
    given = assignments(raw)
    squares = c.dimensions(given)
    if any(len(c.axes(name)) != 1 for name, _ in given):
        raise ContentPlanError("the parent angle method needs three box edge lengths")
    right = None
    for vertex in points:
        first, second = (n for n in points if n != vertex)
        if set(c.axes(vertex + first)).isdisjoint(c.axes(vertex + second)):
            right = vertex
            break
    if right is None or right == points[1]:
        raise ContentPlanError(
            "the parent method requires an acute right-triangle angle"
        )
    legs = tuple(right + n for n in points if n != right)
    if (
        sp.simplify(
            c.squared_length(legs[0], squares) - c.squared_length(legs[1], squares)
        )
        != 0
    ):
        raise ContentPlanError(
            "the parent method requires proven equal perpendicular legs"
        )
    return BoxVertexAngle(
        given, requested, points, squares, right, legs, sp.Integer(45)
    )


def segments(model):
    return tuple(
        sorted(
            tuple(sorted(pair))
            for pair in itertools.combinations(model.vertices, 2)
            if len(c.axes("".join(pair))) > 1
        )
    )
