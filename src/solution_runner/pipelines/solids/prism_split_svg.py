"""Rebuild geometric, vector and coordinate illustrations from their actual points."""

import math
import xml.etree.ElementTree as ET

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _line, _tag
from . import prism_split_scene as geometry
from . import projection_drawing as drawing


def _arrow(root, start, end, style, identifier):
    length = math.dist(start, end)
    if length < 20:
        raise ContentPlanError("the vector arrow is too short for its reviewed head")
    unit = ((end[0] - start[0]) / length, (end[1] - start[1]) / length)
    normal = (-unit[1], unit[0])
    _line(root, start, end, style, identifier)
    points = [
        end,
        tuple(end[j] - 10 * unit[j] + 3 * normal[j] for j in (0, 1)),
        tuple(end[j] - 6 * unit[j] for j in (0, 1)),
        tuple(end[j] - 10 * unit[j] - 3 * normal[j] for j in (0, 1)),
    ]
    ET.SubElement(
        root,
        _tag("polygon"),
        {
            "id": identifier + "-head",
            "fill": style["stroke"],
            "points": " ".join(f"{x:.6f},{y:.6f}" for x, y in points),
        },
    )


def _wireframe(root, vertices, purpose, black):
    hidden = {"A", "C"} if purpose == "geometric" else {"B", "C"}
    for a, b in geometry.EDGES:
        _line(
            root,
            vertices[a],
            vertices[b],
            black | {"stroke-dasharray": "7.5,3" if {a, b} == hidden else "none"},
            "wire-" + a + "-" + b,
        )


def _helpers(root, vertices, m, purpose, black, blue):
    pieces = [
        ("K", "N", blue if purpose != "geometric" else black, False),
        ("K", "M", blue, True),
        ("N", "M", blue if purpose != "geometric" else black, True),
    ]
    if purpose == "geometric":
        pieces.extend(
            (("K", "H", blue, False), ("M", "H", blue, True), ("B", "M", black, True))
        )
        if m.names[0] == "quarter":
            pieces.extend((("C", "E", black, True), ("B", "L", black, True)))
            if m.q["foot"] > 1:
                pieces.append(("B", "E", black, True))
        else:
            pieces.append(("K", "B", black, False))
    for a, b, style, dashed in pieces:
        _line(
            root,
            vertices[a],
            vertices[b],
            style | {"stroke-dasharray": "7.5,3" if dashed else "none"},
            "helper-" + a + "-" + b,
        )


def _arrows(root, vertices, purpose, black):
    if purpose == "vector":
        for name, end, color, dashed in (
            ("a", "A", "#007EA5", False),
            ("b", "C", "#0A990A", True),
            ("c", "B_1", "#8150F9", False),
        ):
            style = black | {
                "stroke": color,
                "stroke-dasharray": "7.5,3" if dashed else "none",
            }
            _arrow(root, vertices["B"], vertices[end], style, "vector-" + name)
    elif purpose == "axes":
        for name in "xyz":
            _arrow(root, vertices["A"], vertices[name], black, "axis-" + name)


def render(m, slot):
    purpose, meta = geometry.template(m, slot)
    root, groups, (black, blue) = drawing.drawing(meta)
    vertices, markers = geometry.scene(m, purpose, meta)
    _wireframe(root, vertices, purpose, black)
    _helpers(root, vertices, m, purpose, black, blue)
    _arrows(root, vertices, purpose, black)
    for i, mark in enumerate(markers):
        for j in (0, 1):
            _line(root, mark[j], mark[j + 1], black, f"right-angle-{i}-{j}")
    return drawing.finish(
        root, groups, meta, vertices, (), [p for mark in markers for p in mark]
    )
