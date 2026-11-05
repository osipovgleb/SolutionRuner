"""Intersect the actual three-vertex plane with all twelve rectangular-box edges."""

import itertools
import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from . import box_coordinates as c
from .box_geometry_input import assignments
from .polyhedron_input import complete_text

PATTERN = rf"[ВB] прямоугольном параллелепипеде\s+{c.HEADER}\s+(?:известны длины ребер\s*:?|известно, что)\s*(.+?)\s*\.\s*Найдите площадь сечения(?: параллелепипеда плоскостью, проходящей|, проходящего) через (?:точки|вершины)\s+({c.VERTEX})\s*,\s*({c.VERTEX})\s+и\s+({c.VERTEX})\s*\."


@dataclass(frozen=True)
class BoxSection:
    given: tuple[tuple[str, sp.Expr], ...]
    points: tuple[str, ...]
    squares: tuple[sp.Expr, ...]
    vertices: tuple[str, ...]
    edge: str
    diagonal: str
    right: str
    answer: sp.Expr


def plane_intersection(coordinates):
    if len(coordinates) != 3:
        raise ContentPlanError("three section points are required")
    a, b, d = (sp.Matrix(p) for p in coordinates)
    normal = (b - a).cross(d - a)
    if normal == sp.zeros(3, 1):
        raise ContentPlanError("three noncollinear section points are required")
    points = set()
    for u, v in itertools.combinations(c.VERTICES, 2):
        if len(c.axes(u + v)) != 1:
            continue
        p, q = sp.Matrix(c.VERTICES[u]), sp.Matrix(c.VERTICES[v])
        start, end = normal.dot(p - a), normal.dot(q - a)
        if start == 0:
            points.add(tuple(p))
        if end == 0:
            points.add(tuple(q))
        if start * end < 0:
            points.add(tuple(p + start / (start - end) * (q - p)))
    return points


def intersection(names):
    if (
        len(names) != 3
        or len(set(names)) != 3
        or any(n not in c.VERTICES for n in names)
    ):
        raise ContentPlanError("three distinct canonical section points are required")
    points = plane_intersection(tuple(c.VERTICES[n] for n in names))
    labels = {p: n for n, p in c.VERTICES.items()}
    if len(points) != 4 or any(p not in labels for p in points):
        raise ContentPlanError(
            "the parent method requires a four-vertex diagonal rectangle"
        )
    names = sorted(labels[p] for p in points)
    origin = names[0]
    edge = [n for n in names[1:] if len(c.axes(origin + n)) == 1]
    diagonal = [n for n in names[1:] if len(c.axes(origin + n)) == 2]
    if len(edge) != 1 or len(diagonal) != 1:
        raise ContentPlanError(
            "a diagonal rectangle with one box-edge direction is required"
        )
    e, d = edge[0], diagonal[0]
    opposite = next(n for n in names if n not in (origin, e, d))
    p, q, r, s = (sp.Matrix(c.VERTICES[n]) for n in (origin, e, opposite, d))
    if p + r != q + s or (q - p).dot(s - p) != 0:
        raise ContentPlanError("the actual section must be rectangular")
    return origin, e, opposite, d


def read_question(html, source=None):
    match = re.fullmatch(PATTERN, complete_text(html, source))
    if match is None:
        raise ContentPlanError(
            "one complete three-vertex rectangular-box section is required"
        )
    given = assignments(match[1])
    squares = c.dimensions(given)
    if any(len(c.axes(name)) != 1 for name, _ in given):
        raise ContentPlanError(
            "the section method requires three independent box edges"
        )
    points = match[2], match[3], match[4]
    vertices = intersection(points)
    a, e, _, d = vertices
    right = next(
        n
        for n in c.VERTICES
        if n not in (a, d) and len(c.axes(a + n)) == 1 and len(c.axes(n + d)) == 1
    )
    edge, diagonal = a + e, a + d
    answer = sp.sqrt(
        c.squared_length(edge, squares) * c.squared_length(diagonal, squares)
    )
    return BoxSection(
        given, points, squares, vertices, edge, diagonal, right, sp.simplify(answer)
    )


def segments(model):
    a, b, d, e = model.vertices
    return tuple(sorted(tuple(sorted(pair)) for pair in ((a, e), (b, d))))
