"""Reviewed source lettering and one affine camera for spatial projection scenes."""

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from importlib.resources import files

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _style
from ..triangles.right.construction_svg import _tag
from .box_svg import _letters, _numbers
from .distance_sources import source_bytes

TEMPLATE_SHA256 = "1c4980d3e372a655dcd7025adb3607919b9db2980020dcbc8ec559411ed35dfb"
PROJECTIONS = (
    (1, 1),
    (1, 1.5),
    (1, 0.6),
    (1.5, 1),
    (0.6, 1),
    (1, 2),
    (2, 1),
    (2, 3),
    (0.6, 3),
    (1.5, 2),
    (0.4, 2),
    (1, 1, 1.5),
    (2, 3, 1.6),
    (2, 5, 2),
)


def template(key):
    raw = (
        files(__package__)
        .joinpath("assets/line-projection-templates.json")
        .read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ContentPlanError("the reviewed line-projection template changed")
    return json.loads(raw)[key]


def drawing(meta):
    root = ET.fromstring(source_bytes(meta["source"]))
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    keep = set(meta["glyph_indices"].values())
    if len(groups) != len(keep) + len(meta["number_labels"]) + len(
        meta.get("discarded_groups", ())
    ):
        raise ContentPlanError("the reviewed projection lettering changed")
    styles = tuple(
        _style(next(e for e in root.findall(_tag("line")) if e.get("stroke") == color))
        | {"stroke-dasharray": "none"}
        for color in (meta.get("black", "#0D0F0F"), "#143B8F")
    )
    for node in list(root):
        if (
            node.tag in {_tag("line"), _tag("path"), _tag("polygon"), _tag("polyline")}
            or node in groups
        ):
            root.remove(node)
    return root, groups, styles


def projector(points, meta, factors):
    old = meta["vertices"]
    origin = old[meta.get("origin", "A")]
    basis = (
        [list(vector) for vector in meta["basis"]]
        if "basis" in meta
        else [
            [
                (old[n][j] - origin[j]) / float(sp.sympify(meta["dimensions"][i]))
                for j in (0, 1)
            ]
            for i, n in enumerate(("B", "D", meta["vertical"]))
        ]
    )
    basis[1] = [basis[1][i] * factors[i] for i in (0, 1)]

    def screen(point):
        return tuple(
            sum(float(point[i]) * basis[i][j] for i in range(3)) for j in (0, 1)
        )

    raw = [screen(p) for p in points.values()]
    old_points = [old[n] for n in points]
    spans = [max(p[j] for p in raw) - min(p[j] for p in raw) for j in (0, 1)]
    old_spans = [
        max(p[j] for p in old_points) - min(p[j] for p in old_points) for j in (0, 1)
    ]
    scale = min(old_spans[j] / spans[j] for j in (0, 1)) * (
        factors[2] if len(factors) == 3 else 1
    )

    def project(point):
        return tuple(origin[j] + scale * v for j, v in enumerate(screen(point)))

    return project, {n: project(p) for n, p in points.items()}


def finish(root, groups, meta, vertices, squares, extra=()):
    for index in meta["glyph_indices"].values():
        root.append(groups[index])
    boxes = _letters(root, groups, meta, vertices)
    _numbers(root, squares, meta, vertices, boxes)
    for node in root.findall(_tag("text")):
        node.text = re.sub(r"√\((\d+)\)", r"√\1", node.text).replace("·√", "√")
    return canvas_svg(
        root, boxes + [(x, y, 0, 0) for x, y in [*vertices.values(), *extra]]
    )
