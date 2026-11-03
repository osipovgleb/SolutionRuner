"""Construct the external altitude rays with audited strokes and outlined letters."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..isosceles.basic_figures import canvas_svg
from ..isosceles.side_altitude_svg import _corner, _place, _style
from ..right.construction_svg import _bounds, _line, _tag
from .height_area_svg import _clear


def _points(alpha):
    gamma = math.radians(float(alpha))
    if not math.pi / 2 < gamma < math.pi:
        raise ContentPlanError(
            "the external angle is indistinguishable from a degenerate SVG configuration"
        )
    c, s = math.cos(gamma), math.sin(gamma)
    if 1 + c < 1e-12:
        raise ContentPlanError("the external construction exceeds SVG precision")
    points = {
        "A": (0, 0),
        "B": (100, 0),
        "C": (100 * c, -100 * s),
        "D": (100 * c * c, -100 * c * s),
        "E": (100 * c, 0),
        "O": (100 * c, -100 * c * s / (1 + c)),
    }
    xs, ys = zip(*points.values())
    scale = 200 / max(max(xs) - min(xs), max(ys) - min(ys))
    edges = ["AB", "AC", "BC", "AD", "DO", "OE", "EA"]
    if any(math.dist(points[e[0]], points[e[1]]) * scale < 9 for e in edges):
        raise ContentPlanError(
            "the external construction collapses at the reviewed SVG scale"
        )
    return {
        k: (12 + (x - min(xs)) * scale, 12 + (y - min(ys)) * scale)
        for k, (x, y) in points.items()
    }


def _labels(root, glyphs, m, points, black):
    boxes = []
    for role in "ABCDEO":
        name = m.name(role)
        x, y = points[role]
        w, h = _bounds(glyphs[name])[2:]
        positions = {
            "A": (x - w - 3, y + 2),
            "B": (x + 2, y + 2),
            "C": (x - w / 2, y - h - 2),
            "D": (x + 3, y - h / 2),
            "E": (x - w - 3, y - h / 2),
            "O": (x - w / 2, y + 3),
        }
        aliases = {"A": "H", "B": "K", "C": "H", "D": "K", "E": "H", "O": "B"}
        x, y = _clear(*positions[role], w, h, boxes, aliases[role])
        _place(root, glyphs, name, x, y, boxes)
    return boxes


def external_svg(m, raw):
    if not 90 < m.alpha < 180:
        raise ContentPlanError(
            "an external altitude diagram requires an obtuse common angle"
        )
    original = ET.fromstring(raw)
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 6:
        raise ContentPlanError("the reviewed ABCDEO altitude lettering changed")
    glyphs = dict(zip("ABCDEO", groups))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    cyan = _style(next(e for e in lines if e.get("stroke") == "#007EA5"))
    points = _points(m.alpha)
    root = ET.Element(_tag("svg"), dict(original.attrib))
    for side in ("AB", "BC", "CA"):
        _line(root, points[side[0]], points[side[1]], black, "side-" + side)
    for side in ("AD", "AE"):
        _line(
            root,
            points[side[0]],
            points[side[1]],
            black | {"stroke-dasharray": "4 4"},
            "extension-" + side,
        )
    for start, foot, style in [("B", "D", blue), ("C", "E", cyan)]:
        _line(root, points[start], points[foot], style, "altitude-" + foot)
        _line(
            root,
            points[foot],
            points["O"],
            style | {"stroke-dasharray": "4 4"},
            "altitude-extension-" + foot,
        )
        _corner(root, points[foot], points[start], points["A"], style, "right-" + foot)
    boxes = _labels(root, glyphs, m, points, black)
    xs, ys = zip(*points.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
