"""Project the actual symmetric tetrahedron and its marked perpendicular foot."""

import math
import xml.etree.ElementTree as ET

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _line, _tag
from . import projection_drawing as drawing
from .box_svg import _clear


def points(m):
    q = m.q
    return {
        "N": sp.zeros(3, 1),
        "B": sp.Matrix([-q["w"] / 2, 0, 0]),
        "C": sp.Matrix([q["w"] / 2, 0, 0]),
        "S": sp.Matrix([0, q["SN"], 0]),
        "A": sp.Matrix([0, q["SN"] - q["x"], q["AM"]]),
        "M": sp.Matrix([0, q["SN"] - q["x"], 0]),
        "x": sp.Matrix([0, q["SN"] - q["x"] / 2, 0]),
    }


def _scene(m, meta, factors):
    p = points(m)
    project, vertices = drawing.projector(p, meta, factors)
    edges = [(a, b) for a in "SABC" for b in "SABC" if a < b]
    solid = {n: vertices[n] for n in "SABC"}
    if (
        not _clear(solid, edges)
        or min(
            math.dist(vertices[a], vertices[b])
            for a, b in (("A", "M"), ("S", "M"), ("M", "N"))
        )
        < 12
    ):
        raise ContentPlanError("the symmetric tetrahedron projection is indistinct")
    delta = min(float(m.q[k]) for k in ("u", "v", "w")) * 0.045
    u, v = p["A"] - p["M"], p["S"] - p["M"]
    u, v = u * (delta / float(u.norm())), v * (delta / float(v.norm()))
    marker = [project(p["M"] + z) for z in (u, u + v, v)]
    return vertices, marker


def scene(m, meta):
    if not (0 < m.q["foot"] < 1):
        raise ContentPlanError("the reviewed tetrahedron scene has its foot inside SN")
    failures = []
    for factors in drawing.PROJECTIONS:
        try:
            return _scene(m, meta, factors)
        except ContentPlanError as exc:
            failures.append(exc)
    raise ContentPlanError(
        "the symmetric tetrahedron needs another reviewed camera"
    ) from failures[-1]


def _ticks(root, vertices, style):
    for a, b, count in (("A", "B", 3), ("A", "C", 3), ("S", "B", 1), ("S", "C", 1)):
        p, q = vertices[a], vertices[b]
        size = math.dist(p, q)
        unit = ((q[0] - p[0]) / size, (q[1] - p[1]) / size)
        for i in range(count):
            center = tuple(
                (p[j] + q[j]) / 2 + (i - (count - 1) / 2) * 2.6 * unit[j]
                for j in (0, 1)
            )
            normal = (-unit[1] * 3.5, unit[0] * 3.5)
            ends = [
                tuple(center[j] + sign * normal[j] for j in (0, 1)) for sign in (-1, 1)
            ]
            _line(root, *ends, style, "equal-" + a + b + "-" + str(i))


def render(m):
    meta = drawing.template("symmetric_tetrahedron")
    root, groups, (black, blue) = drawing.drawing(meta)
    vertices, marker = scene(m, meta)
    ET.SubElement(
        root,
        _tag("polygon"),
        {
            "id": "median-plane",
            "fill": "#143B8F",
            "opacity": "0.5",
            "points": " ".join(
                f"{vertices[n][0]:.6f},{vertices[n][1]:.6f}" for n in "ASN"
            ),
        },
    )
    for a, b, colored, hidden in (
        ("S", "A", True, False),
        ("S", "B", False, False),
        ("S", "C", False, False),
        ("A", "B", False, False),
        ("A", "C", False, True),
        ("B", "C", False, False),
        ("A", "N", True, True),
        ("S", "N", True, False),
        ("A", "M", False, True),
    ):
        style = (blue if colored else black) | {
            "stroke-dasharray": "7.5,3" if hidden else "none"
        }
        _line(root, vertices[a], vertices[b], style, "edge-" + a + "-" + b)
    for i in (0, 1):
        _line(root, marker[i], marker[i + 1], black, "right-angle-" + str(i))
    _ticks(root, vertices, black)
    squares = (m.q["u"] ** 2, m.q["v"] ** 2, m.q["w"] ** 2 / 4)
    return drawing.finish(root, groups, meta, vertices, squares, marker)
