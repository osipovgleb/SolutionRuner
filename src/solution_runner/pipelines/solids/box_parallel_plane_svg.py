"""Project the actual perpendicular foot and preserve the reviewed section style."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from importlib.resources import files

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _style
from ..triangles.right.construction_svg import _line, _tag
from . import box_coordinates as c
from .box_svg import _clear, _letters, _numbers, _wireframe, hidden
from .distance_sources import source_bytes

TEMPLATE_SHA256 = "b8a1bff1066af056311b6eb2be38f0026a923af1101d4f6fcd1cf81aa68cca75"


def template(purpose):
    raw = (
        files(__package__)
        .joinpath("assets/box-parallel-plane-templates.json")
        .read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ContentPlanError("the reviewed parallel-plane projection changed")
    if purpose not in {"side", "top"}:
        raise ContentPlanError("this parallel-plane figure needs review")
    return json.loads(raw)[purpose]


def _projection(m, meta, width_factor, depth_factor):
    old = meta["vertices"]
    origin = old["A"]
    basis = [
        [(old[n][j] - origin[j]) / meta["dimensions"][i] for j in (0, 1)]
        for i, n in enumerate(("B", "D", "A_1"))
    ]
    basis[1][0] *= width_factor
    basis[1][1] *= depth_factor
    points = c.points(tuple(m.q[k] for k in ("a", "b", "height")))

    def screen(point):
        return tuple(
            sum(float(point[i]) * basis[i][j] for i in range(3)) for j in (0, 1)
        )

    raw = {n: screen(p) for n, p in points.items()}
    spans = [
        max(p[j] for p in raw.values()) - min(p[j] for p in raw.values())
        for j in (0, 1)
    ]
    scale = min(175 / spans[0], 140 / spans[1])

    def project(point):
        return tuple(origin[j] + scale * v for j, v in enumerate(screen(point)))

    foot = sp.Matrix([m.q["E_" + axis] for axis in "xyz"])
    vertices = {n: project(p) for n, p in points.items()} | {"E": project(foot)}
    line_start, helper_start = ("B", "A") if m.names[0] == "side" else ("A", "D")
    delta = min(float(m.q[k]) for k in ("a", "b", "height")) * 0.055
    units = [
        (points[n] - foot) * (delta / float((points[n] - foot).norm()))
        for n in (line_start, helper_start)
    ]
    marker = [
        project(foot + units[0]),
        project(foot + units[0] + units[1]),
        project(foot + units[1]),
    ]
    edges = [
        (a, b)
        for a in c.VERTICES
        for b in c.VERTICES
        if a < b and len(c.axes(a + b)) == 1
    ]
    if not _clear(vertices, edges):
        raise ContentPlanError(
            "the perpendicular foot is indistinguishable from the box edges"
        )
    section = ("A_1", "B", "D") if m.names[0] == "side" else ("A", "C", "D_1")
    x, y, z = (vertices[n] for n in section)
    area2 = abs((y[0] - x[0]) * (z[1] - x[1]) - (y[1] - x[1]) * (z[0] - x[0]))
    if area2 / max(math.dist(x, y), math.dist(y, z), math.dist(z, x)) < 10:
        raise ContentPlanError("the section collapses in this projection")
    if min(math.dist(vertices["E"], vertices[n]) for n in c.VERTICES) < 5:
        raise ContentPlanError("the perpendicular foot is too close to a vertex")
    return vertices, marker


def projection(m, meta):
    failures = []
    for width, depth in (
        (1, 1),
        (1, 1.5),
        (1, 0.6),
        (1, 2),
        (1, 0.4),
        (1.5, 1),
        (0.6, 1),
        (2, 1),
        (0.4, 1),
    ):
        try:
            return _projection(m, meta, width, depth)
        except ContentPlanError as exc:
            failures.append(exc)
    raise ContentPlanError(
        "the perpendicular foot needs another reviewed projection"
    ) from failures[-1]


def _construction(root, vertices, marker, purpose, meta, styles):
    black, blue = styles
    section = ("A_1", "B", "D") if purpose == "side" else ("A", "C", "D_1")
    ET.SubElement(
        root,
        _tag("polygon"),
        {
            "id": "section",
            "points": " ".join(
                f"{vertices[n][0]:.6f},{vertices[n][1]:.6f}" for n in section
            ),
            "fill": "#143B8F",
            "opacity": "0.5",
        },
    )
    black["stroke-dasharray"] = "none"
    _wireframe(root, vertices, meta["hidden_corner"], black)
    for a, b in zip(section, section[1:] + section[:1], strict=True):
        _line(
            root,
            vertices[a],
            vertices[b],
            blue | {"stroke-dasharray": "7.5,3" if hidden(a, b, "D") else "none"},
            "section-" + a + "-" + b,
        )
    helpers = (
        (("A", "E"), ("D", "E")) if purpose == "side" else (("D", "E"), ("D_1", "E"))
    )
    for i, (a, b) in enumerate(helpers):
        _line(
            root,
            vertices[a],
            vertices[b],
            (black if i == 0 else blue)
            | {"stroke-dasharray": "none" if a == "A" else "7.5,3"},
            "helper-" + a + "-" + b,
        )
    for i in (0, 1):
        _line(
            root,
            marker[i],
            marker[i + 1],
            black | {"stroke-dasharray": "none"},
            "right-angle-" + str(i),
        )


def render(m):
    meta = template(m.names[0])
    root = ET.fromstring(source_bytes(meta["source"]))
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    keep = set(meta["glyph_indices"].values())
    if len(groups) != len(keep) + len(meta["number_labels"]):
        raise ContentPlanError("the parallel-plane lettering changed")
    black = _style(
        next(e for e in root.findall(_tag("line")) if e.get("stroke") == "#0D0F0F")
    )
    blue = _style(
        next(e for e in root.findall(_tag("line")) if e.get("stroke") == "#143B8F")
    )
    for node in list(root):
        if node.tag in {
            _tag("line"),
            _tag("polygon"),
            _tag("polyline"),
            _tag("path"),
        } or node in [g for i, g in enumerate(groups) if i not in keep]:
            root.remove(node)
    vertices, marker = projection(m, meta)
    _construction(root, vertices, marker, m.names[0], meta, (black, blue))
    for i, group in enumerate(groups):
        if i in keep:
            root.remove(group)
            root.append(group)
    boxes = _letters(root, groups, meta, vertices)
    _numbers(root, m.squares, meta, vertices, boxes)
    return canvas_svg(root, boxes + [(x, y, 0, 0) for x, y in vertices.values()])
