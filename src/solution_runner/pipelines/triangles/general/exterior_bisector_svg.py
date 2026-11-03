"""Draw the opposite exterior-bisector ray when D lies beyond A."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..isosceles.basic_figures import canvas_svg
from ..isosceles.side_altitude_svg import _place, _style
from ..right.construction_svg import _bounds, _line, _tag
from .angle_label_positions import _position


def _points(model):
    a, b, c = (math.radians(float(x)) for x in [model.alpha, model.beta, model.gamma])
    if not all(0 < x < math.pi for x in [a, b, c]):
        raise ContentPlanError("the exterior bisector exceeds SVG precision")
    ac, bc = 100 * math.sin(b) / math.sin(c), 100 * math.sin(a) / math.sin(c)
    if not 1e-6 < min(ac, bc) <= max(ac, bc) < 1e6 or abs(ac - bc) < 1e-8:
        raise ContentPlanError(
            "the external intersection exceeds the reviewed SVG coordinate range"
        )
    points = {
        "A": (0, 0),
        "B": (100, 0),
        "C": (ac * math.cos(a), -ac * math.sin(a)),
        "D": (100 * ac / (ac - bc), 0),
        "E": ((ac + bc) * math.cos(a), -(ac + bc) * math.sin(a)),
    }
    if points["D"][0] >= 0:
        raise ContentPlanError("the opposite exterior bisector must meet AB beyond A")
    xs, ys = zip(*points.values())
    scale = 300 / max(max(xs) - min(xs), max(ys) - min(ys))
    if any(
        math.dist(points[e[0]], points[e[1]]) * scale < 9
        for e in ["AB", "AC", "BC", "CD", "CE", "DE", "AD"]
    ):
        raise ContentPlanError(
            "the distinct exterior-bisector points collapse at the reviewed SVG scale"
        )
    return {
        n: (12 + (x - min(xs)) * scale, 12 + (y - min(ys)) * scale)
        for n, (x, y) in points.items()
    }


def _labels(root, glyphs, model, points):
    boxes = []
    for role in "ABCDE":
        name = model.name(role)
        w, h = _bounds(glyphs[name])[2:]
        x, y = points[role]
        preferred = {
            "A": (x - w / 2, y + 3),
            "B": (x + 3, y + 3),
            "C": (x - w - 3, y - h - 3),
            "D": (x - w / 2, y + 3),
            "E": (x - w - 3, y - h - 3),
        }[role]
        x, y = _position(root, points[role], w, h, boxes, preferred)
        _place(root, glyphs, name, x, y, boxes)
    return boxes


def exterior_svg(model, raw):
    if model.mode != "exterior" or model.alpha <= model.beta:
        raise ContentPlanError(
            "the opposite exterior-bisector diagram requires A greater than B"
        )
    original = ET.fromstring(raw)
    groups = original.findall(_tag("g"))
    if len(groups) != 5:
        raise ContentPlanError("the reviewed ABCDE exterior-bisector lettering changed")
    glyphs = dict(zip("ABCDE", groups))
    lines = original.findall(_tag("line"))
    black, blue = [
        _style(next(e for e in lines if e.get("stroke") == color))
        for color in ["#0D0F0F", "#143B8F"]
    ]
    root = ET.Element(_tag("svg"), dict(original.attrib))
    points = _points(model)
    for side in ["AB", "DA", "AE", "BC", "DE"]:
        _line(root, points[side[0]], points[side[1]], black, side)
    _line(root, points["C"], points["D"], blue, "CD")
    _line(root, (points["D"][0] - 8, points["D"][1]), points["D"], black, "base-cap-D")
    _line(root, points["B"], (points["B"][0] + 8, points["B"][1]), black, "base-cap-B")
    for side in ["CB", "CE"]:
        p, q = (points[n] for n in side)
        dx, dy = q[0] - p[0], q[1] - p[1]
        norm = math.hypot(dx, dy)
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        nx, ny = -2.835 * dy / norm, 2.835 * dx / norm
        _line(
            root,
            (mid[0] - nx, mid[1] - ny),
            (mid[0] + nx, mid[1] + ny),
            black,
            "equal-" + side,
        )
    boxes = _labels(root, glyphs, model, points)
    xs, ys = zip(*points.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
