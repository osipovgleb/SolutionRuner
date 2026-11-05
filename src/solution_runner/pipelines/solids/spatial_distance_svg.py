"""Reuse parent lettering and project the actual altitude onto the box frame."""

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
from .box_svg import _letters, _numbers, _wireframe, hidden, layout
from .distance_sources import source_bytes

TEMPLATE_SHA256 = "0d81a53deebf71ab7671bb1e175b4c1e8c53404e1604540e076782ed59d019c0"


def template():
    raw = files(__package__).joinpath("assets/box-altitude-template.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ContentPlanError("the reviewed altitude projection template changed")
    return json.loads(raw)


def projection(m, vertices):
    p, q, r = (sp.Matrix(c.VERTICES[n]) for n in m.names)
    metric = sp.diag(*m.squares)
    direction = r - q
    fraction = sp.simplify(
        ((p - q).T * metric * direction)[0] / (direction.T * metric * direction)[0]
    )
    foot = q + fraction * direction
    dims = [math.sqrt(float(v)) for v in m.squares]
    origin = vertices["A"]
    basis = [[vertices[n][j] - origin[j] for j in (0, 1)] for n in ("B", "D", "A_1")]

    def project(point):
        return tuple(
            origin[j] + sum(float(point[i]) * basis[i][j] for i in range(3))
            for j in (0, 1)
        )

    delta = min(dims) * 0.055
    units = []
    for v in (p - foot, q - foot):
        norm = math.sqrt(sum(float(v[i]) ** 2 * float(m.squares[i]) for i in range(3)))
        units.append(v * (delta / norm))
    marker = (
        project(foot + units[0]),
        project(foot + units[0] + units[1]),
        project(foot + units[1]),
    )
    return project(foot), marker


def scene_projection(m, meta):
    original = layout(
        meta,
        ((m.names[0], m.names[1]), (m.names[0], m.names[2]), (m.names[1], m.names[2])),
    )
    origin = original["A"]
    basis = [
        (original[n][0] - origin[0], original[n][1] - origin[1])
        for n in ("B", "D", "A_1")
    ]
    depth = next(i for i in (0, 1) if abs(basis[i][1]) > 1)
    edges = [
        (a, b)
        for a in c.VERTICES
        for b in c.VERTICES
        if a < b and len(c.axes(a + b)) == 1
    ]
    for factor in (1, 1.5, 0.6, 2, 0.4):
        vectors = [
            (x, y * factor if i == depth else y) for i, (x, y) in enumerate(basis)
        ]
        vertices = {
            name: tuple(
                origin[j] + sum(point[i] * vectors[i][j] for i in range(3))
                for j in (0, 1)
            )
            for name, point in c.VERTICES.items()
        }
        foot, marker = projection(m, vertices)
        distances = []
        for a, b in edges:
            p, q = vertices[a], vertices[b]
            v = (q[0] - p[0], q[1] - p[1])
            t = max(
                0,
                min(
                    1,
                    sum((foot[i] - p[i]) * v[i] for i in (0, 1))
                    / sum(x * x for x in v),
                ),
            )
            distances.append(math.dist(foot, (p[0] + t * v[0], p[1] + t * v[1])))
        if min(distances) >= 6:
            return vertices, foot, marker
    raise ContentPlanError(
        "the altitude foot cannot be distinguished from the box edges"
    )


def render(m):
    if m.mode == "trapezoid_prism_pentagon_area":
        from .prism_pentagon_cut_svg import render as pentagon

        return pentagon(m)
    if m.mode == "regular_triangle_general_cut_area":
        from .regular_triangle_cut_svg import render as triangle_cut

        return triangle_cut(m)
    if m.mode == "ratio_plane_distance":
        from .spatial_plane_svg import render as ratio

        return ratio(m)
    if m.mode != "box_altitude_comparison":
        from . import spatial_metric_svg

        return spatial_metric_svg.render(m)
    meta = template()
    root = ET.fromstring(source_bytes(meta["source"]))
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    keep = set(meta["glyph_indices"].values())
    if len(groups) != len(keep) + len(meta["number_labels"]):
        raise ContentPlanError("the parent altitude lettering changed")
    for index, group in enumerate(groups):
        if index not in keep:
            root.remove(group)
    lines = root.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#000000"))
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    for node in list(root):
        if node.tag in {_tag("line"), _tag("polygon"), _tag("polyline")}:
            root.remove(node)
    p, q, r = m.names
    vertices, foot, marker = scene_projection(m, meta)
    if min(math.dist(foot, vertices[n]) for n in (q, r)) < 5:
        raise ContentPlanError(
            "the altitude foot cannot be distinguished in this projection"
        )
    vertices["E"] = foot
    _wireframe(root, vertices, meta["hidden_corner"], black)
    for a, b in ((p, r), (q, r), (p, "E")):
        style = blue | {
            "stroke-dasharray": "7.5,3"
            if b == "E" or hidden(a, b, meta["hidden_corner"])
            else "none"
        }
        _line(root, vertices[a], vertices[b], style, "altitude-" + a + "-" + b)
    for index in (0, 1):
        _line(
            root,
            marker[index],
            marker[index + 1],
            blue | {"stroke-dasharray": "none"},
            "right-angle-" + str(index),
        )
    boxes = _letters(root, groups, meta, vertices)
    _numbers(root, m.squares, meta, vertices, boxes)
    return canvas_svg(root, boxes + [(x, y, 0, 0) for x, y in vertices.values()])
