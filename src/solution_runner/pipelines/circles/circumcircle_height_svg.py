"""Place both bases above the circumcenter for the outside-center construction."""

import math
import xml.etree.ElementTree as ET

from ..core.errors import ContentPlanError
from ..triangles.general.angle_label_positions import _position
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _place, _style
from ..triangles.right.construction_svg import _bounds, _line, _tag
from .circumcircle_height_model import DETAIL, SOURCE
from .quantity_sources import source_bytes

CENTER = (110.0, 110.0)
RADIUS = 100.0


def points(model):
    large, small, radius, _ = model.given
    a, b = float(large / radius) * RADIUS / 2, float(small / radius) * RADIUS / 2
    if a >= RADIUS or a <= b:
        raise ContentPlanError("the outside-center bases collapse at SVG precision")
    near, far = math.sqrt(RADIUS**2 - a * a), math.sqrt(RADIUS**2 - b * b)
    if min(a, b, a - b, far - near, near) < 0.05:
        raise ContentPlanError(
            "the outside-center construction collapses at SVG precision"
        )
    x, y = CENTER
    return {
        "A": (x - a, y - near),
        "B": (x + a, y - near),
        "C": (x + b, y - far),
        "D": (x - b, y - far),
        "H": (x, y - near),
        "K": (x, y - far),
        "O": CENTER,
    }


def figure_svg(model, detail):
    original = ET.fromstring(source_bytes(DETAIL if detail else SOURCE))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    names = "ABCDHKO" if detail else "ABCD"
    if len(groups) != len(names):
        raise ContentPlanError("the reviewed trapezoid lettering changed")
    glyphs = dict(zip(names, groups))
    p = points(model)
    black = _style(next(e for e in original.findall(_tag("path")) if e.get("stroke")))
    blue = _style(original.find(_tag("polygon")))
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
    for a, b in zip("ABCD", "BCDA"):
        _line(root, p[a], p[b], blue, "side-" + a + b)
    if detail:
        teal = _style(original.find(_tag("line")))
        _line(root, p["K"], p["O"], teal, "altitude-KO")
        for name in "ABCD":
            _line(root, p["O"], p[name], teal, "radius-O" + name)
    # Include the circular boundary in the shared label collision check.
    obstacle = ET.SubElement(
        root,
        _tag("polyline"),
        {
            "points": " ".join(
                f"{CENTER[0] + RADIUS * math.cos(i * math.pi / 48)},{CENTER[1] + RADIUS * math.sin(i * math.pi / 48)}"
                for i in range(97)
            )
        },
    )
    boxes = []
    for name in names:
        x, y = p[name]
        w, h = _bounds(glyphs[name])[2:]
        preferred = {
            "A": (x - w - 4, y - h / 2),
            "B": (x + 4, y - h / 2),
            "C": (x + 4, y - h - 4),
            "D": (x - w - 4, y - h - 4),
            "H": (x + 4, y + 4),
            "K": (x + 3, y + 2),
            "O": (x + 4, y + 4),
        }[name]
        if name == "H" and CENTER[1] - y < 2 * h + 8 and y - p["K"][1] > h + 5:
            top = y - h - 3
            radial_x = CENTER[0] + (p["C"][0] - CENTER[0]) * (CENTER[1] - top) / (
                CENTER[1] - p["C"][1]
            )
            preferred = (radial_x + 4, top)
        lx, ly = _position(root, p[name], w, h, boxes, preferred)
        _place(root, glyphs, name, lx, ly, boxes)
    root.remove(obstacle)
    root.set(
        "viewBox",
        f"{CENTER[0] - RADIUS} {CENTER[1] - RADIUS} {2 * RADIUS} {2 * RADIUS}",
    )
    return canvas_svg(root, boxes)
