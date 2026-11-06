"""A true two-dimensional BMN triangle retains its source lettering and numbers."""

import math
import xml.etree.ElementTree as ET

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _line, _tag
from . import projection_drawing as drawing
from .box_svg import _clear


def scene(m, meta):
    q = m.q
    x = sp.simplify((q["BM"] ** 2 + q["BN"] ** 2 - q["MN"] ** 2) / (2 * q["BN"]))
    y = sp.sqrt(sp.simplify(q["BM"] ** 2 - x * x))
    p = {
        "B": sp.zeros(3, 1),
        "N": sp.Matrix([q["BN"], 0, 0]),
        "M": sp.Matrix([x, y, 0]),
    }
    for scale in (1, 1.5, 2, 3):
        project, vertices = drawing.projector(p, meta, (1, 1, scale))
        if (
            not _clear(vertices, (("B", "M"), ("M", "N"), ("B", "N")))
            or min(math.dist(vertices[a], vertices[b]) for a in p for b in p if a < b)
            < 14
        ):
            continue
        u, v = p["B"] - p["M"], p["N"] - p["M"]
        u, v = u / u.norm(), v / v.norm()
        cosine = sp.simplify(u.dot(v))
        w = (v - cosine * u) / sp.sqrt(1 - cosine * cosine)
        radius = min(float(q[k]) for k in ("BM", "MN", "BN")) * 0.08
        angle = math.acos(float(cosine))
        arc = [
            project(
                p["M"]
                + radius * (u * math.cos(angle * i / 24) + w * math.sin(angle * i / 24))
            )
            for i in range(25)
        ]
        return vertices, arc
    raise ContentPlanError("the flat midpoint triangle requires another reviewed scale")


def render(m, slot):
    if slot != "image_2":
        raise ContentPlanError(
            "the midpoint triangle belongs to the second proof illustration"
        )
    meta = drawing.template("pyramid_skew_triangle")
    root, groups, (black, blue) = drawing.drawing(meta)
    vertices, arc = scene(m, meta)
    for a, b in (("B", "M"), ("M", "N"), ("B", "N")):
        _line(root, vertices[a], vertices[b], black, "triangle-" + a + "-" + b)
    ET.SubElement(
        root,
        _tag("polyline"),
        blue
        | {
            "id": "midpoint-angle",
            "points": " ".join(f"{x:.6f},{y:.6f}" for x, y in arc),
        },
    )
    return drawing.finish(
        root,
        groups,
        meta,
        vertices,
        tuple(m.q[k] ** 2 for k in ("BM", "MN", "BN")),
        arc,
    )
