"""Build the actual regular polygon with the parent's vector lettering and strokes."""

import math
import xml.etree.ElementTree as ET

from ..core.errors import ContentPlanError
from ..triangles.general.angle_label_positions import _position
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _place, _style
from ..triangles.right.construction_svg import _bounds, _line, _tag
from .quantity_sources import source_bytes

SOURCE = "74e2aecb-16e7-40f6-ab61-27c776153928"
CENTER = (66.704, 66.447)
RADIUS = 66.072


def vertices(n):
    if (
        n < 3
        or n > 2 * math.pi * RADIUS / 0.05
        or 2 * RADIUS * math.sin(math.pi / n) < 0.05
    ):
        raise ContentPlanError(
            "regular polygon vertices collapse at the reviewed SVG precision"
        )
    return [
        (
            CENTER[0]
            + RADIUS * math.cos(math.pi / 2 + math.pi / n + 2 * math.pi * k / n),
            CENTER[1]
            + RADIUS * math.sin(math.pi / 2 + math.pi / n + 2 * math.pi * k / n),
        )
        for k in range(n)
    ]


def figure_svg(model):
    points = vertices(int(model.answer))
    original = ET.fromstring(source_bytes(SOURCE))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 4:
        raise ContentPlanError("the reviewed polygon lettering changed")
    glyphs = dict(zip("ABRO", groups))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    ET.SubElement(
        root,
        _tag("circle"),
        black
        | {
            "id": "circumcircle",
            "cx": str(CENTER[0]),
            "cy": str(CENTER[1]),
            "r": str(RADIUS),
        },
    )
    for i, p in enumerate(points):
        _line(root, p, points[(i + 1) % len(points)], black, "side-" + str(i))
    a, b = points[0], points[-1]
    _line(root, CENTER, a, blue, "radius-OA")
    _line(root, CENTER, b, blue, "radius-OB")
    mid = tuple((x + y) / 2 for x, y in zip(CENTER, a))
    boxes = []
    for name, point in [("A", a), ("B", b), ("O", CENTER), ("R", mid)]:
        w, h = _bounds(glyphs[name])[2:]
        preferred = {
            "A": (a[0] - w - 3, a[1] + 4),
            "B": (b[0] + 3, b[1] + 4),
            "O": (CENTER[0] - w / 2, CENTER[1] - h - 5),
            "R": (CENTER[0] - w - 2, a[1] - h - 3)
            if len(points) == 3
            else (mid[0] - w - 4, mid[1] - h / 2),
        }[name]
        x, y = _position(root, point, w, h, boxes, preferred)
        _place(root, glyphs, name, x, y, boxes)
    root.set(
        "viewBox",
        f"{CENTER[0] - RADIUS} {CENTER[1] - RADIUS} {2 * RADIUS} {2 * RADIUS}",
    )
    return canvas_svg(root, boxes)
