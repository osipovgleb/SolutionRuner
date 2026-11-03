"""Adapt the audited exterior-angle strokes, lettering and arc multiplicities."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..right.construction_svg import _bounds, _line, _tag
from .basic_figures import canvas_svg
from .side_altitude_svg import _place, _style


def _arc(root, center, arms, radius, style, name):
    start, end = arms
    first = math.atan2(start[1] - center[1], start[0] - center[0])
    last = math.atan2(end[1] - center[1], end[0] - center[0])
    delta = (last - first + math.pi) % (2 * math.pi) - math.pi
    a = (center[0] + radius * math.cos(first), center[1] + radius * math.sin(first))
    b = (
        center[0] + radius * math.cos(first + delta),
        center[1] + radius * math.sin(first + delta),
    )
    ET.SubElement(
        root,
        _tag("path"),
        style
        | {
            "id": name,
            "d": f"M{a[0]:.6f},{a[1]:.6f} A{radius},{radius} 0 0 {int(delta > 0)} {b[0]:.6f},{b[1]:.6f}",
        },
    )


def _points(model, vertex_external):
    gamma = math.radians(float(model.apex_angle))
    if not 0 < gamma < math.pi:
        raise ContentPlanError(
            "the diagram angle must remain nondegenerate at SVG precision"
        )
    if vertex_external:
        left, apex = (15.148, 98.392), (137.254, 98.392)
        side = apex[0] - left[0]
        upper = (apex[0] - side * math.cos(gamma), apex[1] - side * math.sin(gamma))
        other = next(v for v in model.base_vertices if v != model.requested)
        points = {other: left, model.apex: apex, model.requested: upper}
        extension = (max(apex[0], upper[0]) + 30, apex[1])
        equal = [(left, apex), (upper, apex)]
        return points, extension, equal, model.apex, model.requested
    center = (
        model.given_vertex
        if model.given_kind == "external_base"
        else model.requested[1]
    )
    other = next(v for v in model.base_vertices if v != center)
    left, right = (13.587, 123.658), (114.673, 123.658)
    top = (
        (left[0] + right[0]) / 2,
        left[1] - (right[0] - left[0]) / (2 * math.tan(gamma / 2)),
    )
    return (
        {other: left, center: right, model.apex: top},
        (173.377, right[1]),
        [(left, top), (right, top)],
        center,
        model.apex,
    )


def _labels(root, glyphs, points, extension, boxes):
    if "D" in glyphs:
        points = points | {"D": extension}
    highest = min(points, key=lambda k: points[k][1])
    leftmost = min(points, key=lambda k: points[k][0])
    for name, point in points.items():
        _, _, width, height = _bounds(glyphs[name])
        if name == highest:
            x, y = point[0] - width / 2, point[1] - height - 1
        else:
            x, y = (
                point[0] - width if name == leftmost else point[0] - width / 2,
                point[1] + 1,
            )
        _place(root, glyphs, name, x, y, boxes)


def exterior_svg(model, raw, vertex_external):
    original = ET.fromstring(raw)
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != (3 if vertex_external else 4):
        raise ContentPlanError("the reviewed exterior-angle lettering changed")
    glyphs = dict(zip("ABCD", groups))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    lines = original.findall(_tag("line"))
    paths = original.findall(_tag("path"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    blue = _style(next(e for e in paths if e.get("stroke") == "#143B8F"))
    cyan = next((e for e in paths if e.get("stroke") == "#007EA5"), None)
    points, extension, equal, center, marked = _points(model, vertex_external)
    vertices = list(points)
    for a, b in [
        (vertices[0], vertices[1]),
        (vertices[1], vertices[2]),
        (vertices[2], vertices[0]),
    ]:
        _line(root, points[a], points[b], black, "side-" + "".join(sorted((a, b))))
    _line(root, points[center], extension, black, "exterior-ray")
    for index, (a, b) in enumerate(equal):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        middle = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        u = (-2.835 * dy / length, 2.835 * dx / length)
        _line(
            root,
            (middle[0] - u[0], middle[1] - u[1]),
            (middle[0] + u[0], middle[1] + u[1]),
            black,
            "equal-" + str(index),
        )
    arm = model.requested if vertex_external else model.apex
    _arc(root, points[center], (points[arm], extension), 5.5, blue, "exterior-angle")
    if cyan is not None:
        ends = [v for v in vertices if v != marked]
        a, b, c = points[ends[0]], points[ends[1]], points[marked]
        distance = abs(
            (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        ) / math.hypot(b[0] - a[0], b[1] - a[1])
        for index, radius in enumerate(
            (min(8, distance / 2), min(10, distance * 0.65))
        ):
            _arc(
                root,
                points[marked],
                (points[ends[0]], points[ends[1]]),
                radius,
                _style(cyan),
                "marked-angle-" + str(index),
            )
    boxes = []
    _labels(root, glyphs, points, extension, boxes)
    coords = list(points.values()) + [extension]
    left, top = min(p[0] for p in coords), min(p[1] for p in coords)
    root.set(
        "viewBox",
        f"{left} {top} {max(p[0] for p in coords) - left} {max(p[1] for p in coords) - top}",
    )
    return canvas_svg(root, boxes)
