"""Draw the external height/bisector intersection using the source's style."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..isosceles.basic_figures import canvas_svg
from ..isosceles.side_altitude_svg import _corner, _place, _style
from ..right.construction_svg import _bounds, _line, _tag
from .height_area_svg import _clear


def _points(theta):
    t = math.radians(float(theta))
    if not math.pi / 4 < t < math.pi / 2:
        raise ContentPlanError("the external construction exceeds SVG precision")
    cx, cy = 100 * math.cos(2 * t), -100 * math.sin(2 * t)
    points = {
        "A": (0, 0),
        "B": (100, 0),
        "C": (cx, cy),
        "D": ((100 + cx) / 2, cy / 2),
        "H": (cx, 0),
        "O": (cx, -cx * math.tan(t)),
    }
    xs, ys = zip(*points.values())
    scale = 300 / max(max(xs) - min(xs), max(ys) - min(ys))
    if any(
        math.dist(points[e[0]], points[e[1]]) * scale < 10
        for e in ["AB", "AC", "BC", "AD", "AH", "AO", "HO"]
    ):
        raise ContentPlanError(
            "the external construction collapses at the reviewed SVG scale"
        )
    return {
        k: (12 + (x - min(xs)) * scale, 12 + (y - min(ys)) * scale)
        for k, (x, y) in points.items()
    }


def _labels(root, glyphs, model, points):
    boxes = []
    for role in "ABCDOH":
        name = model.name(role)
        x, y = points[role]
        w, h = _bounds(glyphs[name])[2:]
        positions = {
            "A": (x + 3, y + 3),
            "B": (x + 3, y + 3),
            "C": (x - w / 2, y - h - 3),
            "D": (x + 3, y - h - 3),
            "O": (x - w / 2, y + 3),
            "H": (x - w - 3, y - h / 2),
        }
        x, y = _clear(*positions[role], w, h, boxes, "H" if role == "H" else "K")
        _place(root, glyphs, name, x, y, boxes)
    return boxes


def external_svg(model, raw):
    original = ET.fromstring(raw)
    glyphs = original.findall(_tag("g"))
    if len(glyphs) != 6:
        raise ContentPlanError("the reviewed ABCDOH lettering changed")
    glyphs = dict(zip("ABCDOH", glyphs))
    lines = original.findall(_tag("line"))
    styles = {
        color: _style(next(e for e in lines if e.get("stroke") == color))
        for color in ["#0D0F0F", "#143B8F", "#007EA5"]
    }
    black, height, bisector = (styles[c] for c in ["#0D0F0F", "#143B8F", "#007EA5"])
    root = ET.Element(_tag("svg"), dict(original.attrib))
    points = _points(model.theta)
    for side, style, dashed in [
        ("AB", black, False),
        ("BC", black, False),
        ("CA", black, False),
        ("CH", height, False),
        ("AD", bisector, False),
        ("AH", black, True),
        ("HO", height, True),
        ("AO", bisector, True),
    ]:
        _line(
            root,
            points[side[0]],
            points[side[1]],
            style | ({"stroke-dasharray": "4 4"} if dashed else {}),
            side,
        )
    _corner(root, points["H"], points["A"], points["C"], height, "right-H")
    t = math.radians(float(model.theta))
    ax, ay = points["A"]
    arc_style = _style(original.find(_tag("path")))
    for i in range(2):
        p, q = [
            (ax + 13 * math.cos(t * n), ay - 13 * math.sin(t * n)) for n in [i, i + 1]
        ]
        ET.SubElement(
            root,
            _tag("path"),
            arc_style
            | {
                "id": "bisected-" + str(i),
                "d": f"M {p[0]} {p[1]} A 13 13 0 0 0 {q[0]} {q[1]}",
            },
        )
    boxes = _labels(root, glyphs, model, points)
    xs, ys = zip(*points.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
