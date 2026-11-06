"""Preserve the source pyramid projection, with actual lengths and angle markers."""

import math
import xml.etree.ElementTree as ET

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _line, _tag
from . import projection_drawing as drawing
from .box_svg import _clear


def points(m):
    a, b, h = (m.q[k] for k in ("a", "b", "H"))
    return {
        "A": sp.zeros(3, 1),
        "B": sp.Matrix([a, 0, 0]),
        "C": sp.Matrix([a, b, 0]),
        "D": sp.Matrix([0, b, 0]),
        "S": sp.Matrix([0, 0, h]),
    }


def _scene(m, meta, factors):
    p = points(m)
    project, vertices = drawing.projector(p, meta, factors)
    edges = [("A", "B"), ("B", "C"), ("C", "D"), ("D", "A")] + [
        ("S", n) for n in "ABCD"
    ]
    if not _clear(vertices, edges):
        raise ContentPlanError(
            "the pyramid projection merges a vertex with another edge"
        )
    S, B, C = (vertices[n] for n in ("S", "B", "C"))
    area2 = abs((B[0] - S[0]) * (C[1] - S[1]) - (B[1] - S[1]) * (C[0] - S[0]))
    if area2 / max(math.dist(S, B), math.dist(S, C), math.dist(B, C)) < 10:
        raise ContentPlanError(
            "the pyramid angle cannot be distinguished in this projection"
        )
    u, v = p["B"] - p["S"], p["C"] - p["S"]
    u = u / u.norm()
    v = v / v.norm()
    theta = math.acos(float(u.dot(v)))
    transverse = (v - u.dot(v) * u) / sp.sqrt(1 - u.dot(v) ** 2)
    radius = 0.14 * min(float(m.q["SB"]), float(m.q["SC"]))
    arc = [
        project(
            p["S"]
            + radius
            * (math.cos(theta * i / 24) * u + math.sin(theta * i / 24) * transverse)
        )
        for i in range(25)
    ]
    vertices["phi"] = project(
        p["S"]
        + 2.8 * radius * (math.cos(theta / 2) * u + math.sin(theta / 2) * transverse)
    )
    delta = 0.08 * min(float(m.q["b"]), float(m.q["SB"]))
    units = [
        (p[n] - p["B"]) * (delta / float((p[n] - p["B"]).norm())) for n in ("S", "C")
    ]
    marker = [
        project(p["B"] + units[0]),
        project(p["B"] + units[0] + units[1]),
        project(p["B"] + units[1]),
    ]
    return vertices, edges, arc, marker


def scene(m, meta):
    failures = []
    for factors in drawing.PROJECTIONS:
        try:
            return _scene(m, meta, factors)
        except ContentPlanError as exc:
            failures.append(exc)
    raise ContentPlanError(
        "the vertex projection requires another reviewed pyramid camera"
    ) from failures[-1]


def render(m):
    if m.symbols.get("scene_family") != "proved_vertex_projection":
        raise ContentPlanError("the pyramid projection style needs review")
    meta = drawing.template("pyramid")
    root, groups, styles = drawing.drawing(meta)
    black, blue = styles
    vertices, edges, arc, marker = scene(m, meta)
    for a, b in edges:
        _line(
            root,
            vertices[a],
            vertices[b],
            black | {"stroke-dasharray": "7.5,3" if "A" in (a, b) else "none"},
            "edge-" + a + "-" + b,
        )
    ET.SubElement(
        root,
        _tag("polyline"),
        blue
        | {
            "id": "projection-angle",
            "points": " ".join(f"{x:.6f},{y:.6f}" for x, y in arc),
        },
    )
    for i in (0, 1):
        _line(root, marker[i], marker[i + 1], blue, "right-angle-" + str(i))
    squares = tuple(m.q[k] ** 2 for k in ("a", "b", "SB"))
    return drawing.finish(root, groups, meta, vertices, squares, [*arc, *marker])
