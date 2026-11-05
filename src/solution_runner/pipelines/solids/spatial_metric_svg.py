"""Preserve the hexagonal pyramid frame and construct the requested triangle altitudes."""

import hashlib
import json
import math
import xml.etree.ElementTree as ET
from importlib.resources import files

from ..core.errors import ContentPlanError
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _style
from ..triangles.right.construction_svg import _line, _tag
from .box_svg import _letters
from .distance_sources import source_bytes

TEMPLATE_SHA256 = "733adfe1d03b01a0f564f95e0abe77b0c912ec7a45c33f6d8e253639d21a059e"


def template():
    raw = files(__package__).joinpath("assets/hex-altitude-template.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ContentPlanError("the reviewed hexagonal altitude template changed")
    return json.loads(raw)


def construction(m, points):
    y, z = m.names[-2:]
    base = float(m.q["b"])
    height = float(m.q["face"])
    fraction = float(m.q["foot"])
    ps, py, pz = (points[n] for n in ("S", y, z))

    def project(p):
        return tuple(
            pz[i]
            + (p[0] + base / 2) / base * (py[i] - pz[i])
            + p[1] / height * (ps[i] - (py[i] + pz[i]) / 2)
            for i in (0, 1)
        )

    foot = (-fraction * base / 2, height * (1 - fraction))
    center = (0, 0)
    result = {"M": project(foot), "H": project(center)}
    markers = {}
    size = min(base, height, float(m.q["e"])) * 0.045
    for name, origin, ends in [
        ("M", foot, [(0, height), (base / 2, 0)]),
        ("H", center, [(0, height), (base / 2, 0)]),
    ]:
        vectors = []
        for end in ends:
            delta = (end[0] - origin[0], end[1] - origin[1])
            norm = math.hypot(*delta)
            if norm < 1e-10:
                raise ContentPlanError(
                    "an altitude endpoint needs a distinct marker construction"
                )
            vectors.append(tuple(v * size / norm for v in delta))
        a, b = vectors
        markers[name] = tuple(
            project(p)
            for p in [
                (origin[0] + a[0], origin[1] + a[1]),
                (origin[0] + a[0] + b[0], origin[1] + a[1] + b[1]),
                (origin[0] + b[0], origin[1] + b[1]),
            ]
        )
    return result, markers


def render(m):
    if m.mode != "hex_vertex_line_distance":
        raise ContentPlanError("this regular solid needs no new diagram")
    meta = template()
    root = ET.fromstring(source_bytes(meta["source"]))
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != len(meta["glyph_indices"]):
        raise ContentPlanError("the hexagonal source lettering changed")
    blue = _style(
        next(n for n in root.findall(_tag("line")) if n.get("stroke") == "#143B8F")
    )
    for node in list(root):
        if node.get("stroke") == "#143B8F":
            root.remove(node)
    points = {k: tuple(v) for k, v in meta["vertices"].items()}
    moved, markers = construction(m, points)
    points.update(moved)
    _x, u, v, y, z = m.names
    segments = {
        tuple(sorted((u, v))),
        tuple(sorted((y, z))),
        tuple(sorted((y, "M"))),
        ("H", "S"),
    }
    if m.q["foot"] < 0:
        segments.add(("M", "S"))
    for a, b in sorted(segments):
        _line(
            root,
            points[a],
            points[b],
            blue | {"stroke-dasharray": "7.5,3"},
            "altitude-" + a + "-" + b,
        )
    for name, corners in markers.items():
        for i in (0, 1):
            _line(
                root,
                corners[i],
                corners[i + 1],
                blue | {"stroke-dasharray": "none"},
                "right-angle-" + name + "-" + str(i),
            )
    boxes = _letters(root, groups, meta, points)
    return canvas_svg(root, boxes + [(x, y, 0, 0) for x, y in points.values()])
