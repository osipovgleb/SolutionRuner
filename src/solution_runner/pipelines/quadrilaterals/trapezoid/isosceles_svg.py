"""Actual isosceles-trapezoid altitudes in the audited parent's drawing style."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ...triangles.general.angle_label_positions import _position
from ...triangles.isosceles.basic_figures import canvas_svg
from ...triangles.isosceles.side_altitude_svg import _corner, _place, _style
from ...triangles.right.construction_svg import _bounds, _line, _tag
from .quantity_sources import source_bytes

CE = "42c396d3-3418-40f8-b80e-1eb6102702a1"
MARKED = "a7aa0827-7b1f-4364-8469-437dfe2fe497"
PLAIN = "d64f66e0-9b41-447f-8d93-e95acc9eb921"


def points(m, source):
    small, large, height, projection = map(
        float, (m.small, m.large, m.height, m.projection)
    )
    extent = max(large, height)
    if not math.isfinite(extent) or extent <= 0:
        raise ContentPlanError("the trapezoid exceeds SVG precision")
    scale = 260 / extent
    if min(small, projection, height) * scale < 0.01:
        raise ContentPlanError("distinct trapezoid points collapse at SVG precision")
    p = {
        "A": (0, height),
        "B": (projection, 0),
        "C": (projection + small, 0),
        "D": (large, height),
    }
    p["E" if source == CE else "H"] = (
        projection + small if source == CE else projection,
        height,
    )
    return {name: (12 + x * scale, 12 + y * scale) for name, (x, y) in p.items()}


def _labels(root, glyphs, p):
    boxes = []
    for name, point in p.items():
        width, height = _bounds(glyphs[name])[2:]
        x, y = point
        preferred = (
            (x - width - 3, y + 3)
            if name == "A"
            else (
                (x - width / 2, y - height - 3)
                if name in "BC"
                else (x + 3, y + 3)
                if name == "D"
                else (x - width / 2, y + 3)
            )
        )
        x, y = _position(root, point, width, height, boxes, preferred)
        _place(root, glyphs, name, x, y, boxes)
    return boxes


def figure_svg(m, source):
    if source not in {CE, MARKED, PLAIN}:
        raise ContentPlanError("a reviewed trapezoid height style is required")
    original = ET.fromstring(source_bytes(source))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 5:
        raise ContentPlanError("the audited trapezoid lettering changed")
    glyphs = dict(zip("ABCDE" if source == CE else "ABCDH", groups))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    color = "#007EA5" if source == MARKED else "#143B8F"
    altitude = _style(next(e for e in lines if e.get("stroke") == color))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    p = points(m, source)
    for edge in ("AB", "BC", "CD", "DA"):
        _line(root, p[edge[0]], p[edge[1]], black, "side-" + edge)
    start, foot = ("C", "E") if source == CE else ("B", "H")
    _line(root, p[start], p[foot], altitude, "height-" + start + foot)
    vertex = "D" if source == MARKED else "A"
    size = min(
        7.688, 0.35 * math.dist(p[start], p[foot]), 0.35 * math.dist(p[vertex], p[foot])
    )
    _corner(root, p[foot], p[start], p[vertex], altitude, "right-" + foot, size=size)
    if source == MARKED:
        tick = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
        for edge in ("AB", "CD"):
            a, b = (p[n] for n in edge)
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            size = min(2.835, 0.1 * length)
            center = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            u = (-size * dy / length, size * dx / length)
            _line(
                root,
                (center[0] - u[0], center[1] - u[1]),
                (center[0] + u[0], center[1] + u[1]),
                tick,
                "equal-" + edge,
            )
    boxes = _labels(root, glyphs, p)
    xs, ys = zip(*p.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
