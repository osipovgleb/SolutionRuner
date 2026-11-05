"""Use the shared plane intersection for top-edge and vertical-midpoint sections."""

import re
from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from . import box_coordinates as c
from .box_geometry_input import assignments
from .box_section_model import plane_intersection
from .polyhedron_input import complete_text

PATTERN = rf"[ВB] прямоугольном параллелепипеде\s+{c.HEADER}\s+(.+?)\s*\.\s*Точка K\s*[—–-]\s*середина ребра\s+({c.SEGMENT})\s*\.\s*Найдите площадь сечения, проходящего через точки\s+({c.VERTEX})\s*,\s*({c.VERTEX})\s+и\s+K\s*\."


@dataclass(frozen=True)
class MidpointSection:
    given: tuple[tuple[str, sp.Expr], ...]
    midpoint_edge: str
    squares: tuple[sp.Expr, ...]
    vertices: tuple[str, ...]
    extra_points: tuple[tuple[str, tuple[sp.Expr, ...]], ...]
    edge: str
    diagonal: str
    right: str

    def length(self, a, b):
        points = {**c.VERTICES, **dict(self.extra_points)}
        return sp.sqrt(
            sp.simplify(
                sum(
                    (x - y) ** 2 * s
                    for x, y, s in zip(points[a], points[b], self.squares)
                )
            )
        )

    @property
    def answer(self):
        a, b, _, d = self.vertices
        return sp.simplify(self.length(a, b) * self.length(a, d))


def read_question(html, source=None):
    match = re.fullmatch(PATTERN, complete_text(html, source, extra_identifiers=("K",)))
    if match is None:
        raise ContentPlanError(
            "one complete top-edge midpoint section condition is required"
        )
    given = assignments(re.sub(r"\bребро\s+", "", match[1]))
    squares = c.dimensions(given)
    midpoint_edge, a, b = match.groups()[1:]
    if any(len(c.axes(n)) != 1 for n, _ in given) or c.axes(midpoint_edge) != (2,):
        raise ContentPlanError(
            "three box edges and a vertical-edge midpoint are required"
        )
    if (
        a == b
        or c.VERTICES[a][2] != 1
        or c.VERTICES[b][2] != 1
        or len(c.axes(a + b)) != 1
    ):
        raise ContentPlanError("two adjacent top vertices are required")
    a, b = sorted((a, b))
    u, v = c.endpoints(midpoint_edge)
    midpoint = tuple(
        sp.Rational(x + y, 2) for x, y in zip(c.VERTICES[u], c.VERTICES[v])
    )
    points = plane_intersection((c.VERTICES[a], c.VERTICES[b], midpoint))
    extra = points - set(c.VERTICES.values())
    if len(points) != 4 or len(extra) != 2 or midpoint not in extra:
        raise ContentPlanError(
            "the midpoint must be a corner of the rectangular section"
        )
    other = next(p for p in extra if p != midpoint)
    if other[2] != sp.Rational(1, 2) or any(x not in (0, 1) for x in other[:2]):
        raise ContentPlanError(
            "the fourth section point must bisect another vertical edge"
        )
    labels = {midpoint: "K", other: "K_1"}
    axis = c.axes(a + b)[0]
    near_a = next(p for p in extra if p[axis] == c.VERTICES[a][axis])
    near_b = next(p for p in extra if p[axis] == c.VERTICES[b][axis])
    pa, pb, pc, pd = map(sp.Matrix, (c.VERTICES[a], c.VERTICES[b], near_b, near_a))
    if pa + pc != pb + pd or (pb - pa).dot(pd - pa) != 0:
        raise ContentPlanError("the actual midpoint section must be rectangular")
    right = next(n for n, p in c.VERTICES.items() if p == (*near_a[:2], 1))
    vertices = (a, b, labels[near_b], labels[near_a])
    return MidpointSection(
        given,
        midpoint_edge,
        squares,
        vertices,
        (("K", midpoint), ("K_1", other)),
        a + b,
        a + labels[near_a],
        right,
    )
