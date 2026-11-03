"""Draw the circumcenter outside or on the base using the parent's lettering."""

import math
import xml.etree.ElementTree as ET

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.general.angle_label_positions import _position
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _corner, _place, _style
from ..triangles.right.construction_svg import _bounds, _line, _tag
from .circumcircle_isosceles_model import DETAIL, SOURCE, kind
from .quantity_sources import source_bytes

CENTER = (80.0, 80.0)
RADIUS = 66.0


def points(model):
    a, b = model.given
    h = sp.sqrt(a * a - b * b / 4)
    half = float(b / model.answer) * RADIUS / 2
    altitude = float(h / model.answer) * RADIUS
    if min(half, altitude) < 0.5 or (
        kind(model) == "obtuse" and RADIUS - altitude < 0.5
    ):
        raise ContentPlanError(
            "the isosceles construction collapses at reviewed SVG precision"
        )
    y = CENTER[1] + altitude - RADIUS
    return {
        "A": (CENTER[0] - half, y),
        "B": (CENTER[0] + half, y),
        "C": (CENTER[0], CENTER[1] - RADIUS),
        "H": (CENTER[0], y),
        "O": CENTER,
    }


def _coincident(root, glyphs, point, black, boxes):
    w1, h1 = _bounds(glyphs["O"])[2:]
    w2, h2 = _bounds(glyphs["H"])[2:]
    left = point[0] - (w1 + w2 + 10) / 2
    bottom = point[1] + 4 + max(h1, h2)
    _place(root, glyphs, "O", left, bottom - h1, boxes)
    _place(root, glyphs, "H", left + w1 + 10, bottom - h2, boxes)
    for index, dy in enumerate([-1.5, 1.5]):
        _line(
            root,
            (left + w1 + 2, bottom - h2 * 0.45 + dy),
            (left + w1 + 8, bottom - h2 * 0.45 + dy),
            black,
            "merged-equal-" + str(index),
        )


def _labels(root, glyphs, p, detail, black):
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
    names = ["A", "B", "C", "H", "O", "R_AO", "R_CO"] if detail else ["A", "B", "C"]
    if detail and p["H"] == p["O"]:
        _coincident(root, glyphs, p["H"], black, boxes)
        names = [name for name in names if name not in {"H", "O"}]
    mid_ao = tuple((x + y) / 2 for x, y in zip(p["A"], p["O"]))
    mid_co = tuple((x + y) / 2 for x, y in zip(p["C"], p["O"]))
    for name in names:
        point = mid_ao if name == "R_AO" else mid_co if name == "R_CO" else p[name]
        x, y = point
        w, h = _bounds(glyphs[name])[2:]
        preferred = {
            "A": (x - w - 4, y + 4),
            "B": (x + 4, y + 4),
            "C": (x - w / 2, y - h - 4),
            "H": (x + 4, y + 4),
            "O": (x + 4, y + 4),
            "R_AO": (x - w - 4, y + 4),
            "R_CO": (x - w - 4, y - h / 2),
        }[name]
        lx, ly = _position(root, point, w, h, boxes, preferred)
        _place(root, glyphs, name, lx, ly, boxes)
    root.remove(obstacle)
    return boxes


def figure_svg(model, detail):
    original = ET.fromstring(source_bytes(DETAIL if detail else SOURCE))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    names = ("A", "B", "C", "R_AO", "R_CO", "H", "O") if detail else ("A", "B", "C")
    if len(groups) != len(names):
        raise ContentPlanError("the reviewed isosceles lettering changed")
    glyphs = dict(zip(names, groups))
    p = points(model)
    if kind(model) == "right":
        p["H"] = p["O"] = CENTER
        p["A"] = (CENTER[0] - RADIUS, CENTER[1])
        p["B"] = (CENTER[0] + RADIUS, CENTER[1])
    black = _style(next(e for e in original.findall(_tag("path")) if e.get("stroke")))
    triangle = _style(original.find(_tag("polygon")))
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
    for a, b in [("A", "B"), ("B", "C"), ("C", "A")]:
        _line(root, p[a], p[b], triangle, "side-" + a + b)
    if detail:
        blue = _style(original.find(_tag("line")))
        _line(root, p["O"], p["A"], blue, "radius-OA")
        _line(root, p["C"], p["H"], black, "height-CH")
        _line(root, p["C"], p["O"], black, "radius-CO")
        marker = _style(
            next(e for e in original.iter(_tag("line")) if e.get("stroke") == "#000000")
        )
        size = min(7.688, math.dist(p["C"], p["H"]) / 2, math.dist(p["A"], p["H"]) / 2)
        _corner(root, p["H"], p["A"], p["C"], marker, "right-AHC", size=size)
    boxes = _labels(root, glyphs, p, detail, black)
    root.set(
        "viewBox",
        f"{CENTER[0] - RADIUS} {CENTER[1] - RADIUS} {2 * RADIUS} {2 * RADIUS}",
    )
    return canvas_svg(root, boxes)
