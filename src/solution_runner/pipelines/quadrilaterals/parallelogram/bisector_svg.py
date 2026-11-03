"""Build actual bisector and rhombus geometry with the parent's outlined lettering."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ...triangles.general.angle_label_positions import _position
from ...triangles.isosceles.angle_svg import _arc
from ...triangles.isosceles.basic_figures import canvas_svg
from ...triangles.isosceles.side_altitude_svg import _place, _style
from ...triangles.right.construction_svg import _bounds, _line, _tag
from .quantity_sources import source_bytes

RATIO_SOURCE = "08c781f3-a920-469b-a381-c6e4e0584a5e"
DOUBLE_SOURCE = "32680c37-6527-4f57-b91a-d33736438451"
RHOMBUS_SOURCE = "76657e56-90d6-44c5-a20d-50c62d7badd6"
RATIO_KEY = "quantity_bisector_ratio"
RHOMBUS_KEY = "quantity_rhombus_angle"


def points(m):
    if m.mode == "rhombus_angle":
        angle = math.radians(float(m.angle_a))
        a, b, cosine, sine = 1, 1, math.cos(angle), math.sin(angle)
    else:
        a, b = map(float, (m.first, m.second))
        cosine, sine = 0.6, 0.8
    p = {
        "A": (0, 0),
        "B": (a * cosine, -a * sine),
        "C": (b + a * cosine, -a * sine),
        "D": (b, 0),
    }
    if m.mode == "bisector_ratio":
        p["L"] = (a, 0)
    xs, ys = zip(*p.values())
    extent = max(max(xs) - min(xs), max(ys) - min(ys))
    if not math.isfinite(extent) or extent <= 0:
        raise ContentPlanError("the bisector geometry exceeds SVG precision")
    scale = 260 / extent
    if min(a, b) * sine * scale < 0.01:
        raise ContentPlanError("distinct bisector vertices collapse at SVG precision")
    return {
        name: (12 + (x - min(xs)) * scale, 12 + (y - min(ys)) * scale)
        for name, (x, y) in p.items()
    }


def _labels(root, glyphs, p):
    boxes = []
    for name, point in p.items():
        width, height = _bounds(glyphs[name])[2:]
        x, y = point
        preferred = (
            (x - width - 3, y + 3)
            if name == "A"
            else (
                (x - width - 3, y - height - 3)
                if name == "B"
                else (x + 3, y - height - 3)
                if name == "C"
                else (x + 3, y + 3)
                if name == "D"
                else (x - width / 2, y + 3)
            )
        )
        x, y = _position(root, point, width, height, boxes, preferred)
        _place(root, glyphs, name, x, y, boxes)
    return boxes


def figure_svg(m):
    rhombus = m.mode == "rhombus_angle"
    original = ET.fromstring(source_bytes(RHOMBUS_SOURCE if rhombus else RATIO_SOURCE))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    names = "ABDC" if rhombus else "ABCDL"
    if len(groups) != len(names):
        raise ContentPlanError("the audited bisector lettering changed")
    glyphs = dict(zip(names, groups))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") in {"#000000", "#0D0F0F"}))
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    arc_style = _style(original.find(_tag("path")))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    p = points(m)
    for edge in ("AB", "BC", "CD", "DA"):
        _line(root, p[edge[0]], p[edge[1]], black, "side-" + edge)
    if rhombus:
        for diagonal in m.diagonals:
            _line(root, p[diagonal[0]], p[diagonal[1]], blue, "diagonal-" + diagonal)
        first, vertex, last = m.known
        radius = min(
            8, 0.3 * math.dist(p[first], p[vertex]), 0.3 * math.dist(p[last], p[vertex])
        )
        _arc(root, p[vertex], (p[first], p[last]), radius, arc_style, "given-angle")
    else:
        _line(root, p["B"], p["L"], blue, "bisector-BL")
        radius = min(8, *(0.3 * math.dist(p["B"], p[name]) for name in "ALC"))
        for first, last in (("A", "L"), ("L", "C")):
            _arc(
                root,
                p["B"],
                (p[first], p[last]),
                radius,
                arc_style,
                "half-angle-" + first + last,
            )
    boxes = _labels(root, glyphs, p)
    xs, ys = zip(*p.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
