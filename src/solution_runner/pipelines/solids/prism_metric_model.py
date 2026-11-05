"""Compute prism metrics from actual vertices, then select the parent's geometric witness."""

from dataclasses import dataclass

import sympy as sp

from ..core.errors import ContentPlanError
from . import regular_prism_geometry as g

KINDS = {
    "metric_distance",
    "metric_vertex_angle",
    "metric_tangent",
    "metric_line_angle",
}


@dataclass(frozen=True)
class PrismMetric:
    kind: str
    body: str
    edge: sp.Expr
    requested: tuple[str, ...]
    answer: sp.Expr
    method: str
    height_ratio: sp.Expr = sp.S.One
    helper: tuple[str, ...] = ()
    cosine: sp.Expr = sp.S.Zero
    tangent: sp.Expr = sp.S.Zero

    @property
    def points(self):
        return g.frame(self.body, self.height_ratio)

    @property
    def scene(self):
        if self.method == "cube_equilateral":
            return tuple(sorted(self.helper))
        if self.kind == "metric_distance":
            return tuple(sorted((*self.requested, *self.helper)))
        if self.kind in {"metric_vertex_angle", "metric_tangent"}:
            a, v, b = self.requested
            return (v, *sorted((a, b)))
        return tuple(
            sorted("".join(sorted(g.names(line, 2))) for line in self.requested)
        )


def _layer(point):
    return int(point.endswith("_1"))


def _right_vertex(requested):
    a, v, b = requested
    for vertical, far in ((a, b), (b, a)):
        if (
            vertical[0] == v[0]
            and _layer(vertical) != _layer(v)
            and _layer(far) == _layer(vertical)
        ):
            return vertical, far
    raise ContentPlanError(
        "the prism parent needs a right triangle with a vertical leg"
    )


def _line_witness(body, points, lines):
    endpoints = [g.names(line, 2) for line in lines]
    if body == "cube":
        common = set(endpoints[0]) & set(endpoints[1])
        triangle = tuple(sorted(set(endpoints[0] + endpoints[1])))
        if (
            len(common) != 1
            or len(triangle) != 3
            or any(
                g.squared(points, a + b) != 2
                for a, b in (
                    (triangle[0], triangle[1]),
                    (triangle[1], triangle[2]),
                    (triangle[0], triangle[2]),
                )
            )
        ):
            raise ContentPlanError(
                "the cube parent needs an equilateral face-diagonal triangle"
            )
        return "cube_equilateral", triangle
    if body == "triangle":
        vertical = next(
            (i for i, pair in enumerate(endpoints) if pair[0][0] == pair[1][0]), None
        )
        if vertical is None:
            raise ContentPlanError(
                "one vertical edge and one face diagonal are required"
            )
        pair = endpoints[1 - vertical]
        if _layer(pair[0]) == _layer(pair[1]) or pair[0][0] == pair[1][0]:
            raise ContentPlanError("a square-face diagonal is required")
        bottom = next(n for n in pair if not _layer(n))
        upper = next(n for n in pair if _layer(n))
        return "square_face", (bottom, bottom + "_1", upper)
    if body == "square":
        if any(g.squared(points, line) != 4 for line in lines):
            raise ContentPlanError(
                "the square-prism parent uses space diagonals of length twice the base edge"
            )
        lower = tuple(next(n for n in pair if not _layer(n)) for pair in endpoints)
        if g.squared(points, "".join(lower)) != 1:
            raise ContentPlanError(
                "the parent center triangle needs adjacent base vertices"
            )
        return "center_equilateral", lower
    if any(
        g.squared(points, line) != 1 or _layer(pair[0]) != _layer(pair[1])
        for line, pair in zip(lines, endpoints)
    ):
        raise ContentPlanError("two horizontal regular-hexagon side lines are required")
    direction = g.vector(points, lines[1])
    for origin in endpoints[0]:
        for other in points:
            if other in endpoints[0] or _layer(other) != _layer(origin):
                continue
            candidate = g.vector(points, origin + other)
            if candidate.dot(candidate) == 1 and candidate.cross(direction) == sp.zeros(
                3, 1
            ):
                return "hexagon_parallel", (origin, other)
    raise ContentPlanError(
        "no adjacent-side parallel translation matches the parent method"
    )


def solve(kind, body, edge, requested, height_ratio=sp.S.One):
    if (
        kind not in KINDS
        or edge.is_positive is not True
        or height_ratio.is_positive is not True
    ):
        raise ContentPlanError(
            "a reviewed metric and positive prism dimensions are required"
        )
    points = g.frame(body, height_ratio)
    if kind == "metric_distance":
        a, b = requested
        length = g.squared(points, a + b)
        helper = () if _layer(a) == _layer(b) else (a[0] + ("_1" if _layer(b) else ""),)
        if body != "hexagon" or length not in ({4} if not helper else {4, 5}):
            raise ContentPlanError(
                "the distance parent needs a reviewed hexagonal chord"
            )
        if a == b or length == 0:
            raise ContentPlanError("two distinct prism points are required")
        return PrismMetric(
            kind,
            body,
            edge,
            requested,
            sp.simplify(edge * sp.sqrt(length)),
            "chord_distance" if not helper else "right_distance",
            height_ratio,
            helper,
        )
    if kind == "metric_line_angle":
        u, v = (g.vector(points, line) for line in requested)
        c = g.cosine(u, v, lines=True)
        method, helper = _line_witness(body, points, requested)
        expected = sp.sqrt(2) / 2 if body == "triangle" else sp.Rational(1, 2)
        if c != expected:
            raise ContentPlanError(
                "the line angle differs from the reviewed geometric method"
            )
        return PrismMetric(
            kind, body, edge, requested, g.degrees(c), method, height_ratio, helper, c
        )
    a, v, b = requested
    u = g.vector(points, v + a)
    w = g.vector(points, v + b)
    c = g.cosine(u, w)
    if body == "hexagon" and len({_layer(n) for n in requested}) == 1:
        lengths = sorted((g.squared(points, v + a), g.squared(points, v + b)))
        if lengths != [1, 4]:
            raise ContentPlanError(
                "the base-angle parent uses one side and one long diagonal"
            )
        if kind == "metric_tangent":
            raise ContentPlanError("the tangent parent needs a vertical right triangle")
        helper = ()
        method = "hexagon_bisector"
    else:
        helper = _right_vertex(requested)
        if (
            body != "hexagon"
            or g.squared(points, "".join(helper)) not in {3, 4}
            or c <= 0
        ):
            raise ContentPlanError(
                "the parent needs an acute angle with a short or long hexagonal chord"
            )
        method = "right_vertex"
    if c == 0 and kind == "metric_tangent":
        raise ContentPlanError("the tangent of a right angle is undefined")
    tangent = sp.simplify(sp.sqrt(1 - c * c) / c) if c else sp.S.Zero
    answer = tangent if kind == "metric_tangent" else g.degrees(c)
    return PrismMetric(
        kind, body, edge, requested, answer, method, height_ratio, helper, c, tangent
    )
