"""Read complete edge/face-diagonal line angles and use actual box coordinates."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from . import box_coordinates as c
from .box_geometry_input import assignments, text

PATTERN = rf"[ВB] прямоугольном параллелепипеде {c.HEADER} известны длины ребер\s+(.+?)\s*\.\s*Найдите синус угла между прямыми\s+({c.SEGMENT})\s+и\s+({c.SEGMENT})\s*\."


@dataclass(frozen=True)
class BoxLineAngle:
    given: tuple[tuple[str, sp.Expr], ...]
    lines: tuple[str, str]
    squares: tuple[sp.Expr, ...]
    edge: str
    diagonal: str
    right: str
    answer: sp.Expr


def read_question(html, source=None):
    match = re.fullmatch(PATTERN, text(html, source))
    if match is None:
        raise ContentPlanError("one complete box line-sine question is required")
    given = assignments(match[1])
    squares = c.dimensions(given)
    if any(len(c.axes(name)) != 1 for name, _ in given):
        raise ContentPlanError("the parent method needs three box edge lengths")
    lines = match[2], match[3]
    ordered = sorted(lines, key=lambda name: len(c.axes(name)))
    edge, diagonal = ordered
    if (
        len(c.axes(edge)) != 1
        or len(c.axes(diagonal)) != 2
        or c.axes(edge)[0] not in c.axes(diagonal)
    ):
        raise ContentPlanError(
            "an edge parallel to a face diagonal's plane is required"
        )
    a, b = c.endpoints(diagonal)
    axis = c.axes(edge)[0]
    point = list(c.VERTICES[b])
    point[axis] = c.VERTICES[a][axis]
    right = next(n for n, p in c.VERTICES.items() if p == tuple(point))
    opposite = c.squared_length(a + right, squares)
    hyp = c.squared_length(diagonal, squares)
    return BoxLineAngle(
        given, lines, squares, edge, diagonal, right, sp.sqrt(opposite / hyp)
    )


def segments(model):
    a, b = c.endpoints(model.diagonal)
    axis = next(i for i in range(3) if i not in c.axes(model.diagonal))
    other = []
    for name in (a, b):
        point = list(c.VERTICES[name])
        point[axis] = 1 - point[axis]
        other.append(next(n for n, p in c.VERTICES.items() if p == tuple(point)))
    return tuple(sorted({tuple(sorted((a, b))), tuple(sorted(other))}))
