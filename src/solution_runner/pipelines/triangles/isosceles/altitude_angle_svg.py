"""Adapt the parent's blue side altitude and outlined ABCD lettering."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..right.construction_svg import _bounds, _line, _tag
from .basic_figures import canvas_svg
from .side_altitude_svg import _corner, _place, _style


def _labels(root, glyphs, model, points, black, boxes):
    p, q, c = model.altitude_vertex, model.other_base_vertex, model.apex
    for name in (p, q):
        x, y = points[name]
        width = _bounds(glyphs[name])[2]
        _place(root, glyphs, name, x - width if name == p else x, y + 2, boxes)
    x, y = points[c]
    width, height = _bounds(glyphs[c])[2:]
    if model.topology == 0:
        dw, dh = _bounds(glyphs["D"])[2:]
        start = x - (width + dw + 10) / 2
        bottom = y - 3
        _place(root, glyphs, c, start, bottom - height, boxes)
        _place(root, glyphs, "D", start + width + 10, bottom - dh, boxes)
        for index, dy in enumerate((-1.5, 1.5)):
            _line(
                root,
                (start + width + 2, bottom - dh / 2 + dy),
                (start + width + 8, bottom - dh / 2 + dy),
                black,
                "coincident-equal-" + str(index),
            )
    else:
        _place(root, glyphs, c, x - width / 2, y - height - 2, boxes)
        dx, dy = points["D"]
        dw, dh = _bounds(glyphs["D"])[2:]
        _place(
            root,
            glyphs,
            "D",
            dx + 3 if model.topology > 0 else dx - dw - 3,
            dy - dh / 2,
            boxes,
        )


def altitude_svg(model, raw):
    original = ET.fromstring(raw)
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 4:
        raise ContentPlanError("the reviewed altitude-angle lettering changed")
    glyphs = dict(zip("ABCD", groups))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    # A schematic needs the correct foot location; no numeric angles are printed.
    gamma = math.radians({1: 60, 0: 90, -1: 120}[model.topology])
    p, q = (12, 120), (116, 120)
    c = (64, 120 - 52 / math.tan(gamma / 2))
    v = (c[0] - q[0], c[1] - q[1])
    scale = ((p[0] - q[0]) * v[0] + (p[1] - q[1]) * v[1]) / sum(z * z for z in v)
    d = c if model.topology == 0 else (q[0] + scale * v[0], q[1] + scale * v[1])
    points = {
        model.altitude_vertex: p,
        model.other_base_vertex: q,
        model.apex: c,
        "D": d,
    }
    root = ET.Element(_tag("svg"), dict(original.attrib))
    for name, a, b in [("base", p, q), ("side-left", p, c), ("side-right", q, c)]:
        _line(root, a, b, black, name)
    if model.topology < 0:
        _line(root, c, d, black | {"stroke-dasharray": "4 4"}, "side-extension")
    _line(root, p, d, blue, "altitude")
    _corner(root, d, p, q, blue, "right-D")
    boxes = []
    _labels(root, glyphs, model, points, black, boxes)
    xs, ys = zip(*points.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
