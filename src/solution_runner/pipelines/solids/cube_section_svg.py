"""Project the verified corner section in the parent's wireframe and lettering."""

import xml.etree.ElementTree as ET
from copy import deepcopy

from ..core.errors import ContentPlanError
from ..triangles.general.angle_label_positions import _position
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _place, _style
from ..triangles.right.construction_svg import _bounds, _line, _tag
from .cube_section_model import VERTICES
from .cube_sources import source_bytes

SOURCE = "a3eeb27f-7a83-4249-be6f-e1c84176b2df"
KEY = "cube_midpoint_section"
NATIVE = {
    "K": frozenset(("A", "A_1")),
    "L": frozenset(("A_1", "D_1")),
    "M": frozenset(("A_1", "B_1")),
}
HIDDEN = {frozenset(e) for e in [("A", "D"), ("D", "C"), ("D", "D_1")]}


def compatible(model):
    return {name: frozenset((a, b)) for name, a, b in model.midpoints} == NATIVE


def project(p):
    x, y, z = p
    return 17.9441 + 106.5693 * x + 38.7764 * y, 149.4358 - 38.6758 * y - 90.2197 * z


def midpoint_positions(model):
    return {
        name: tuple((x + y) / 2 for x, y in zip(VERTICES[a], VERTICES[b]))
        for name, a, b in model.midpoints
    }


def hidden_face(a, b):
    fixed = [(i, x) for i, (x, y) in enumerate(zip(a, b)) if x == y and x in (0, 1)]
    if len(fixed) != 1:
        raise ContentPlanError("the section side must lie in exactly one cube face")
    axis, value = fixed[0]
    return value == {0: 0, 1: 1, 2: 0}[axis]


def figure_svg(model):
    original = ET.fromstring(source_bytes(SOURCE))
    root = deepcopy(original)
    glyph_groups = [
        g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))
    ]
    names = ("A", "B", "C", "D", "A_1", "C_1", "D_1", "B_1", "L", "M", "K")
    if len(glyph_groups) != len(names):
        raise ContentPlanError("the reviewed cube lettering changed")
    glyphs = dict(zip(names, glyph_groups))
    root_glyphs = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    for name, g in zip(names, root_glyphs):
        if name in {"K", "L", "M"}:
            root.remove(g)
    for e in list(root):
        if (
            e.tag == _tag("line")
            or e.get("stroke") == "#143B8F"
            or e.tag == _tag("polygon")
            and e.get("fill") == "#143B8F"
        ):
            root.remove(e)
    black = _style(
        next(e for e in original.findall(_tag("line")) if e.get("stroke") == "#0D0F0F")
    )
    blue = _style(
        next(e for e in original.findall(_tag("line")) if e.get("stroke") == "#143B8F")
    )
    keys = list(VERTICES)
    for i, a in enumerate(keys):
        for b in keys[i + 1 :]:
            if sum(abs(x - y) for x, y in zip(VERTICES[a], VERTICES[b])) != 1:
                continue
            style = black | (
                {"stroke-dasharray": "7.5,3"} if frozenset((a, b)) in HIDDEN else {}
            )
            _line(
                root,
                project(VERTICES[a]),
                project(VERTICES[b]),
                style,
                "edge-" + a + "-" + b,
            )
    p = midpoint_positions(model)
    q = {name: project(point) for name, point in p.items()}
    for a, b in [("K", "L"), ("L", "M"), ("M", "K")]:
        style = blue | (
            {"stroke-dasharray": "7.5,3"} if hidden_face(p[a], p[b]) else {}
        )
        _line(root, q[a], q[b], style, "section-" + a + b)
    ET.SubElement(
        root,
        _tag("polygon"),
        {
            "id": "section-fill",
            "opacity": "0.5",
            "fill": "#143B8F",
            "points": " ".join(f"{q[n][0]:.6f},{q[n][1]:.6f}" for n in "KLMK"),
        },
    )
    boxes = [_bounds(glyphs[name]) for name in names if name not in {"K", "L", "M"}]
    for name in "KLM":
        x, y = q[name]
        w, h = _bounds(glyphs[name])[2:]
        preferred = (x + 4 if x > 90 else x - w - 4, y + 4 if y > 85 else y - h - 4)
        lx, ly = _position(root, q[name], w, h, boxes, preferred)
        _place(root, glyphs, name, lx, ly, boxes)
    return canvas_svg(root, boxes)
