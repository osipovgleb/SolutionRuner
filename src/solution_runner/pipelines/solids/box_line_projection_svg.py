"""Draw the actual projection foot on either reviewed rectangular-box section."""

import math
import xml.etree.ElementTree as ET

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _line, _tag
from . import box_coordinates as c
from . import projection_drawing as drawing
from .box_svg import _clear, _wireframe, hidden


def _scene(m, meta, factors):
    points = c.points(tuple(m.q[k] for k in ("a", "b", "height")))
    project, vertices = drawing.projector(points, meta, factors)
    foot = sp.Matrix([m.q["E_" + axis] for axis in "xyz"])
    vertices["H"] = project(foot)
    face = m.names[0] == "face"
    section = ("A_1", "B", "C", "D_1") if face else ("A", "A_1", "C_1", "C")
    edges = [
        (a, b)
        for a in c.VERTICES
        for b in c.VERTICES
        if a < b and len(c.axes(a + b)) == 1
    ]
    if (
        not _clear(vertices, edges)
        or min(math.dist(vertices["H"], vertices[n]) for n in c.VERTICES) < 6
    ):
        raise ContentPlanError("the box projection foot cannot be distinguished")
    p, q, r = (vertices[n] for n in section[:3])
    area2 = abs((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))
    if area2 / max(math.dist(p, q), math.dist(q, r), math.dist(r, p)) < 12:
        raise ContentPlanError("the projection section collapses in this camera")
    delta = min(float(m.q[k]) for k in ("a", "b", "height")) * 0.045
    names = ("C", "C_1") if face else ("A", "B")
    units = [
        (points[n] - foot) * (delta / float((points[n] - foot).norm())) for n in names
    ]
    marker = [
        project(foot + units[0]),
        project(foot + units[0] + units[1]),
        project(foot + units[1]),
    ]
    return vertices, section, marker


def scene(m, meta):
    failures = []
    for factors in drawing.PROJECTIONS:
        try:
            return _scene(m, meta, factors)
        except ContentPlanError as exc:
            failures.append(exc)
    raise ContentPlanError(
        "the projection requires another reviewed box camera"
    ) from failures[-1]


def render(m):
    if m.names[0].startswith("midpoint_"):
        from .box_midpoint_projection_svg import render as midpoint

        return midpoint(m)
    meta = drawing.template("box_" + m.names[0])
    root, groups, styles = drawing.drawing(meta)
    black, blue = styles
    vertices, section, marker = scene(m, meta)
    ET.SubElement(
        root,
        _tag("polygon"),
        {
            "id": "section",
            "fill": "#143B8F",
            "opacity": "0.5",
            "points": " ".join(
                f"{vertices[n][0]:.6f},{vertices[n][1]:.6f}" for n in section
            ),
        },
    )
    back = meta["hidden_corner"]
    _wireframe(root, vertices, back, black)
    for a, b in zip(section, section[1:] + section[:1], strict=True):
        _line(
            root,
            vertices[a],
            vertices[b],
            blue | {"stroke-dasharray": "7.5,3" if hidden(a, b, back) else "none"},
            "section-" + a + "-" + b,
        )
    helpers = ("C_1", "B") if m.names[0] == "face" else ("B", "A_1")
    for name in helpers:
        _line(
            root,
            vertices[name],
            vertices["H"],
            black | {"stroke-dasharray": "7.5,3"},
            "projection-" + name + "-H",
        )
    for i in (0, 1):
        _line(root, marker[i], marker[i + 1], black, "right-angle-" + str(i))
    return drawing.finish(root, groups, meta, vertices, m.squares, marker)
