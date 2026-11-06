"""Draw the actual edge midpoints and their perpendicular projection."""

import math

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _line
from . import box_coordinates as c
from . import projection_drawing as drawing
from .box_svg import _clear, _wireframe


def _scene(m, meta, factors):
    points = c.points(tuple(m.q[k] for k in ("a", "b", "height")))
    project, vertices = drawing.projector(points, meta, factors)
    points.update(
        {n: sp.Matrix([m.q[n + "_" + axis] for axis in "xyz"]) for n in ("E", "F")}
    )
    vertices.update({n: project(points[n]) for n in ("E", "F")})
    target = "B" if m.names[0] == "midpoint_side" else "A_1"
    edges = [
        (a, b)
        for a in c.VERTICES
        for b in c.VERTICES
        if a < b and len(c.axes(a + b)) == 1
    ]
    if (
        not _clear({n: vertices[n] for n in c.VERTICES}, edges)
        or min(
            math.dist(vertices[a], vertices[b])
            for a, b in (("E", "F"), ("E", target), ("F", target))
        )
        < 12
    ):
        raise ContentPlanError("the midpoint projection triangle is too small")
    p, q, r = (vertices[n] for n in ("E", "F", target))
    area = abs((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))
    if area / max(math.dist(p, q), math.dist(q, r), math.dist(r, p)) < 8:
        raise ContentPlanError("the midpoint projection triangle collapses")
    delta = min(float(m.q[k]) for k in ("a", "b", "height")) * 0.055
    foot = points[target]
    u, v = (points[n] - foot for n in ("E", "F"))
    u, v = u * (delta / float(u.norm())), v * (delta / float(v.norm()))
    marker = [project(foot + u), project(foot + u + v), project(foot + v)]
    return vertices, target, marker


def scene(m, meta):
    failures = []
    for factors in drawing.PROJECTIONS:
        try:
            return _scene(m, meta, factors)
        except ContentPlanError as exc:
            failures.append(exc)
    raise ContentPlanError(
        "the edge midpoints require another reviewed camera"
    ) from failures[-1]


def render(m):
    meta = drawing.template("box_" + m.names[0])
    root, groups, styles = drawing.drawing(meta)
    black, blue = styles
    vertices, target, marker = scene(m, meta)
    _wireframe(root, vertices, meta["hidden_corner"], black)
    _line(
        root,
        vertices["E"],
        vertices["F"],
        blue | {"stroke-dasharray": "7.5,3"},
        "midpoint-E-F",
    )
    _line(
        root,
        vertices[target],
        vertices["F"],
        black | {"stroke-dasharray": "7.5,3"},
        "midpoint-projection",
    )
    for i in (0, 1):
        _line(root, marker[i], marker[i + 1], black, "right-angle-" + str(i))
    return drawing.finish(root, groups, meta, vertices, m.squares, marker)
