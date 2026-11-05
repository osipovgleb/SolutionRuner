"""Relabel a reviewed section by an actual square-base symmetry, keeping vector glyphs."""

import hashlib
import itertools
import json
import xml.etree.ElementTree as ET
from importlib.resources import files
from types import SimpleNamespace

from ..core.errors import ContentPlanError
from ..triangles.general.simple_angle_figures import _remapped
from ..triangles.right.construction_svg import _tag
from . import box_coordinates as c
from .box_midpoint_sources import FIGURES, source_bytes

GLYPH_SHA = "70cd6adf8ec26a95ab1ec68adeee82fff38f088b492891b3c236b61152f7fc48"

SOLUTION = "2efaf127-5406-4957-bb86-06b45529b757"
CONDITION = "58692e88-f3ef-4bb5-964c-2214c02500d3"
GLYPHS = {
    SOLUTION: ("A", "C", "B", "D", "D_1", "C_1", "B_1", "A_1", "K", "K_1"),
    CONDITION: ("A", "C", "B", "D", "D_1", "C_1", "B_1", "A_1", "K"),
}


def lower_midpoint(m):
    return next(
        n for n, p in c.VERTICES.items() if p == (*dict(m.extra_points)["K"][:2], 0)
    )


def compatible(m, source, role):
    kind, lower, top = FIGURES[source]
    return (
        kind == role
        and lower == lower_midpoint(m)
        and (role == "condition" or set(top) == set(m.vertices[:2]))
    )


def mapping(m, source):
    _, lower, top = FIGURES[source]
    for permutation in itertools.permutations("ABCD"):
        names = dict(zip("ABCD", permutation))
        if any(
            len(c.axes(a + b)) != len(c.axes(names[a] + names[b]))
            for a, b in itertools.combinations("ABCD", 2)
        ):
            continue
        names.update({n + "_1": v + "_1" for n, v in tuple(names.items())})
        if names[lower] == lower_midpoint(m) and {names[n] for n in top} == set(
            m.vertices[:2]
        ):
            return names | {"K": "K", "K_1": "K_1"}
    raise ContentPlanError("the midpoint section has no reviewed square-base symmetry")


def figure_svg(m, source):
    names = mapping(m, source)
    raw = files(__package__).joinpath("assets/box-midpoint-glyphs.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != GLYPH_SHA:
        raise ContentPlanError("the reviewed midpoint glyph bounds changed")
    boxes = json.loads(raw)[source]
    root = ET.fromstring(source_bytes(source))
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != len(boxes):
        raise ContentPlanError("the reviewed midpoint lettering changed")
    for group, (x, y, w, h) in zip(groups, boxes):
        ET.SubElement(
            group,
            _tag("rect"),
            {
                "x": str(x),
                "y": str(y),
                "width": str(w),
                "height": str(h),
                "fill": "none",
                "stroke": "none",
            },
        )
    return _remapped(
        SimpleNamespace(name=names.__getitem__), ET.tostring(root), GLYPHS[source]
    )
