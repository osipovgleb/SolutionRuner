"""Rebuild the ratio section and its actual perpendicular in the parent frame."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from importlib.resources import files

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _style
from ..triangles.right.construction_svg import _line, _tag
from .box_svg import _letters
from .distance_sources import source_bytes

TEMPLATE_SHA256 = "bfc6d35111f9785d0636aa5c699e6d45a15e813aa16f38afc98af36ef0f417a7"


def template():
    raw = files(__package__).joinpath("assets/ratio-plane-template.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ContentPlanError("the reviewed ratio-section frame changed")
    return json.loads(raw)


def geometry(m):
    q = m.q
    a = q["a"]
    radius = q["R"]
    h = q["H"]
    r = q["fraction"]
    points = {
        "A": sp.Matrix([radius, 0, 0]),
        "B": sp.Matrix([-radius / 2, a / 2, 0]),
        "C": sp.Matrix([-radius / 2, -a / 2, 0]),
        "S": sp.Matrix([0, 0, h]),
    }
    A, B, C, S = (points[n] for n in "ABCS")
    points.update(
        H=(B + C) / 2,
        K=A + r * (B - A),
        L=A + r * (C - A),
        M=S + r * (C - S),
        N=S + r * (B - S),
    )
    points.update(R=(points["K"] + points["L"]) / 2, Q=(points["M"] + points["N"]) / 2)
    direction = S - A
    origin = points["R"]
    points["P"] = A + (origin - A).dot(direction) / direction.dot(direction) * direction
    return points


def projection(points, meta):
    A = points["A"]
    basis = sp.Matrix.hstack(*(points[n] - A for n in ("B", "C", "S")))
    origin = sp.Matrix(meta["vertices"]["A"])
    screen = sp.Matrix.hstack(
        *(sp.Matrix(meta["vertices"][n]) - origin for n in ("B", "C", "S"))
    )
    matrix = screen * basis.inv()

    def project(p):
        return tuple(float(v) for v in origin + matrix * (p - A))

    return project


def marker(points, project, origin, first, second, size):
    p = points[origin]
    vectors = []
    for name in (first, second):
        vector = points[name] - p
        length = vector.norm()
        if length == 0:
            raise ContentPlanError("coincident feet need a different reviewed diagram")
        vectors.append(vector * (size / length))
    a, b = vectors
    return tuple(project(v) for v in (p + a, p + a + b, p + b))


def _frame():
    meta = template()
    root = ET.fromstring(source_bytes(meta["source"]))
    children = list(root)
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    body = [deepcopy(children[i]) for i in meta["body_indices"]]
    if len(groups) != len(meta["glyph_indices"]):
        raise ContentPlanError("the parent section lettering changed")
    for n in list(root):
        if n.tag in {_tag("line"), _tag("polygon"), _tag("polyline")} or n in groups:
            root.remove(n)
    original_a = tuple(meta["vertices"]["A"])
    meta["vertices"]["A"][0] = meta["vertices"]["S"][0] + 1.35 * (
        original_a[0] - meta["vertices"]["S"][0]
    )
    for edge in body:
        for endpoint in ("1", "2"):
            position = tuple(float(edge.get(axis + endpoint)) for axis in ("x", "y"))
            if math.dist(position, original_a) < 0.01:
                edge.set("x" + endpoint, str(meta["vertices"]["A"][0]))
    meta["glyph_indices"].pop("T")
    meta["glyph_boxes"].pop("T")
    return root, meta, groups, body


def render(m):
    if m.mode != "ratio_plane_distance":
        raise ContentPlanError("this section uses its compatible native illustration")
    root, meta, groups, body = _frame()
    black = _style(body[0])
    blue = black | {"stroke": "#143B8F"}
    points = geometry(m)
    project = projection(points, meta)
    screen = {name: project(p) for name, p in points.items()}
    if math.dist(screen["S"], screen["P"]) < 2:
        raise ContentPlanError("coincident section feet cannot be labelled clearly")
    ET.SubElement(
        root,
        _tag("polygon"),
        {
            "opacity": "0.5",
            "fill": "#143B8F",
            "points": " ".join(
                f"{screen[n][0]:.6f},{screen[n][1]:.6f}" for n in ("L", "M", "N", "K")
            ),
            "id": "section-KNML",
        },
    )
    for n in body:
        root.append(n)
    for a, b, dashed in [
        ("S", "H", False),
        ("A", "H", True),
        ("R", "P", True),
    ]:
        _line(
            root,
            screen[a],
            screen[b],
            black | ({"stroke-dasharray": "7.5,3"} if dashed else {}),
            "construction-" + a + "-" + b,
        )
    if m.q["small_foot"] > 1:
        _line(
            root,
            screen["S"],
            screen["P"],
            black | {"stroke-dasharray": "7.5,3"},
            "extension-S-P",
        )
    for a, b, dashed in [
        ("L", "M", True),
        ("M", "N", False),
        ("N", "K", False),
        ("K", "L", True),
        ("Q", "R", True),
    ]:
        _line(
            root,
            screen[a],
            screen[b],
            blue | {"stroke-dasharray": "7.5,3" if dashed else "none"},
            "section-" + a + "-" + b,
        )
    size = min(m.q["a"], m.q["e"]) * sp.Rational(1, 35)
    for origin, first, second in [("P", "R", "A"), ("H", "A", "B")]:
        corners = marker(points, project, origin, first, second, size)
        for i in (0, 1):
            _line(
                root,
                corners[i],
                corners[i + 1],
                black | {"stroke-dasharray": "none"},
                "right-" + origin + "-" + str(i),
            )
    for index in meta["glyph_indices"].values():
        root.append(groups[index])
    boxes = _letters(root, groups, meta, screen)
    x, y = screen["L"]
    ox, oy, width, height = meta["glyph_boxes"]["L"]
    x, y = x - width - 3, y + 3
    groups[meta["glyph_indices"]["L"]].set(
        "transform", f"translate({x - ox:.6f} {y - oy:.6f})"
    )
    boxes.append((x, y, width, height))
    return canvas_svg(root, boxes + [(x, y, 0, 0) for x, y in screen.values()])
