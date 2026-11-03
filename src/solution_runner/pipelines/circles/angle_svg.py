"""Draw the actual three-arc circle with the parent's strokes and outlined letters."""

import math
import xml.etree.ElementTree as ET

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.rectangle_proofs import value
from ..triangles.general.angle_label_positions import _position
from ..triangles.isosceles.angle_svg import _arc
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _place, _style
from ..triangles.right.construction_svg import _bounds, _line, _tag
from .angle_sources import source_bytes

SOURCE = "d98c679b-1fdf-4382-9fad-5c11e6512d0f"
CENTER = (80.0, 80.0)
RADIUS = 62.362


def radial(angle, radius=RADIUS):
    radians = math.radians(float(angle))
    return CENTER[0] + radius * math.cos(radians), CENTER[1] + radius * math.sin(
        radians
    )


def points(model):
    a, b = map(float, model.given)
    result = {"A": radial(-40 - a), "C": radial(-40), "B": radial(-40 + b)}
    if min(math.dist(result[x], result[y]) for x, y in ("AC", "CB", "AB")) < 0.05:
        raise ContentPlanError("distinct circle vertices collapse at SVG precision")
    return result


def _labels(root, glyphs, model, p):
    boxes = []
    for name in "ABC":
        point = p[name]
        width, height = _bounds(glyphs[name])[2:]
        angle = math.degrees(math.atan2(point[1] - CENTER[1], point[0] - CENTER[0]))
        x, y = radial(angle, RADIUS + max(width, height) / 2 + 5)
        x, y = _position(
            root, point, width, height, boxes, (x - width / 2, y - height / 2)
        )
        _place(root, glyphs, name, x, y, boxes)
    for identifier, amount, angle in (
        ("arc-AC", model.given[0], -40 - float(model.given[0]) / 2),
        ("arc-BC", model.given[1], -40 + float(model.given[1]) / 2),
    ):
        text = value(amount).replace("{,}", ",") + "°"
        if "\\" in text:
            raise ContentPlanError(
                "the circle arc label needs an exact decimal representation"
            )
        font, width, height = 14, 7 * len(text), 16
        x, y = radial(angle, RADIUS + width / 2 + 9)
        x, y = _position(
            root, (x, y), width, height, boxes, (x - width / 2, y - height / 2)
        )
        label = ET.SubElement(
            root,
            _tag("text"),
            {
                "id": identifier,
                "x": f"{x:.6f}",
                "y": f"{y + 12:.6f}",
                "font-family": "Times New Roman, Times, serif",
                "font-size": str(font),
                "fill": "#0D0F0F",
            },
        )
        label.text = text
        boxes.append((x, y, width, height))
    return boxes


def figure_svg(model):
    original = ET.fromstring(source_bytes(SOURCE))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 5:
        raise ContentPlanError("the reviewed circle lettering changed")
    glyphs = dict(zip("ABC", groups[:3]))
    black = _style(original.find(_tag("circle")))
    blue = _style(original.find(_tag("line")))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    ET.SubElement(
        root,
        _tag("circle"),
        black
        | {
            "cx": str(CENTER[0]),
            "cy": str(CENTER[1]),
            "r": str(RADIUS),
        },
    )
    p = points(model)
    for edge in ("CA", "CB"):
        _line(root, p[edge[0]], p[edge[1]], blue, "chord-" + edge)
    size = min(9, 0.2 * math.dist(p["C"], p["A"]), 0.2 * math.dist(p["C"], p["B"]))
    _arc(root, p["C"], (p["A"], p["B"]), size, blue, "angle-ACB")
    boxes = _labels(root, glyphs, model, p)
    root.set(
        "viewBox",
        f"{CENTER[0] - RADIUS} {CENTER[1] - RADIUS} {2 * RADIUS} {2 * RADIUS}",
    )
    return canvas_svg(root, boxes)
