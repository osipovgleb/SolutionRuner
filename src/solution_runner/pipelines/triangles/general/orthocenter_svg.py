"""Draw all three altitudes, their true extensions and coincident right-angle points."""

import itertools
import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..isosceles.basic_figures import canvas_svg
from ..isosceles.side_altitude_svg import _corner, _place, _style
from ..right.construction_svg import _bounds, _line, _tag
from .height_area_svg import _extension


def _points(model):
    alpha, beta, gamma = (
        math.radians(float(a)) for a in [model.alpha, model.beta, model.gamma]
    )
    if not all(0 < a < math.pi for a in [alpha, beta, gamma]):
        raise ContentPlanError("the orthocenter construction exceeds SVG precision")
    length = 100 * math.sin(beta) / math.sin(gamma)
    if not 1e-6 < length < 1e6:
        raise ContentPlanError("the triangle exceeds the reviewed SVG coordinate range")
    cx, cy = length * math.cos(alpha), -length * math.sin(alpha)
    if abs(cy) < 1e-8 or math.hypot(cx - 100, cy) < 1e-8:
        raise ContentPlanError(
            "the triangle height is indistinguishable at SVG precision"
        )
    norm = cx * cx + cy * cy
    t = 100 * (100 - cx) / ((cx - 100) ** 2 + cy * cy)
    points = {
        "A": (0, 0),
        "B": (100, 0),
        "C": (cx, cy),
        "D": (100 + t * (cx - 100), t * cy),
        "E": (100 * cx * cx / norm, 100 * cx * cy / norm),
        "F": (cx, 0),
        "O": (cx, cx * (100 - cx) / cy),
    }
    if model.gamma == 90:
        points.update({n: points["C"] for n in "DEO"})
    xs, ys = zip(*points.values())
    scale = 300 / max(max(xs) - min(xs), max(ys) - min(ys))
    edges = ["AB", "AC", "BC", "AD", "BE", "CF", "AF", "FO", "AO"]
    if model.gamma != 90:
        edges += ["CD", "CE", "CO", "DO", "EO"]
    if any(math.dist(points[e[0]], points[e[1]]) * scale < 9 for e in edges):
        raise ContentPlanError(
            "the distinct orthocenter points collapse at the reviewed SVG scale"
        )
    return {
        k: (12 + (x - min(xs)) * scale, 12 + (y - min(ys)) * scale)
        for k, (x, y) in points.items()
    }


def _intersects(p, q, box):
    x, y, w, h = box
    low, high = 0.0, 1.0
    for axis, start, end in [(0, x - 1, x + w + 1), (1, y - 1, y + h + 1)]:
        delta = q[axis] - p[axis]
        if abs(delta) < 1e-10:
            if not start <= p[axis] <= end:
                return False
        else:
            first, last = sorted(((start - p[axis]) / delta, (end - p[axis]) / delta))
            low, high = max(low, first), min(high, last)
            if low > high:
                return False
    return True


def _position(root, point, w, h, boxes, preferred):
    segments = []
    for line in root.findall(_tag("line")):
        segments.append(
            tuple(
                tuple(float(line.get(axis + str(i))) for axis in ["x", "y"])
                for i in [1, 2]
            )
        )
    for polyline in root.findall(_tag("polyline")):
        points = [
            tuple(map(float, p.split(","))) for p in polyline.get("points").split()
        ]
        segments.extend(itertools.pairwise(points))
    x, y = point
    candidates = [preferred]
    for gap in [4, 8, 12, 20, 30, 40]:
        candidates.extend(
            [
                (x - w - gap, y - h - gap),
                (x + gap, y - h - gap),
                (x - w - gap, y + gap),
                (x + gap, y + gap),
                (x - w / 2, y - h - gap),
                (x - w / 2, y + gap),
                (x - w - gap, y - h / 2),
                (x + gap, y - h / 2),
            ]
        )
    for x, y in candidates:
        if any(
            x < bx + bw + 2 and x + w + 2 > bx and y < by + bh + 2 and y + h + 2 > by
            for bx, by, bw, bh in boxes
        ):
            continue
        if not any(_intersects(p, q, (x, y, w, h)) for p, q in segments):
            return x, y
    raise ContentPlanError(
        "the orthocenter labels cannot be placed without crossing the construction"
    )


def _labels(root, glyphs, model, points, black):
    groups = []
    for role, point in points.items():
        shared = next((g for g in groups if math.dist(g[0], point) < 1e-6), None)
        if shared is None:
            groups.append((point, [role]))
        else:
            shared[1].append(role)
    boxes = []
    center = sum(points[n][0] for n in "ABC") / 3
    for (x, y), roles in groups:
        names = [model.name(n) for n in roles]
        widths = [_bounds(glyphs[n])[2] for n in names]
        height = max(_bounds(glyphs[n])[3] for n in names)
        width = sum(widths) + 10 * (len(names) - 1)
        role = roles[0]
        positions = {
            "A": (x - width - 3, y + 3),
            "B": (x + 3, y + 3),
            "C": (x - width / 2, y - height - 3),
            "D": (x - width - 3 if x < center else x + 3, y - height / 2),
            "E": (x - width - 3 if x < center else x + 3, y - height / 2),
            "F": (x - width / 2, y + 3),
            "O": (x - width - 3, y - height - 3),
        }
        x, y = _position(root, (x, y), width, height, boxes, positions[role])
        if len(names) > 1:
            boxes.append((x, y, width, height))
        for i, name in enumerate(names):
            _place(root, glyphs, name, x, y, boxes)
            x += widths[i]
            if i + 1 < len(names):
                for dy in [-1.5, 1.5]:
                    _line(
                        root,
                        (x + 2, y + height / 2 + dy),
                        (x + 8, y + height / 2 + dy),
                        black,
                        f"merged-{role}-{i}-{dy}",
                    )
                x += 10
    return boxes


def orthocenter_svg(model, raw):
    original = ET.fromstring(raw)
    groups = original.findall(_tag("g"))
    if len(groups) != 7:
        raise ContentPlanError("the reviewed ABCDEFO lettering changed")
    glyphs = dict(zip("ABCDEFO", groups))
    lines = original.findall(_tag("line"))
    black, blue = [
        _style(next(e for e in lines if e.get("stroke") == color))
        for color in ["#0D0F0F", "#143B8F"]
    ]
    points = _points(model)
    root = ET.Element(_tag("svg"), dict(original.attrib))
    for side in ["AB", "BC", "CA"]:
        _line(root, points[side[0]], points[side[1]], black, side)
    for origin, foot, side in [("A", "D", "BC"), ("B", "E", "CA"), ("C", "F", "AB")]:
        _extension(root, points, side, foot, black)
        _line(root, points[origin], points[foot], blue, origin + foot)
        _extension(
            root,
            points,
            origin + foot,
            "O",
            blue,
            name="altitude-extension-" + origin + foot,
        )
        vertex = next(n for n in side if math.dist(points[n], points[foot]) > 1e-6)
        _corner(
            root, points[foot], points[origin], points[vertex], blue, "right-" + foot
        )
    boxes = _labels(root, glyphs, model, points, black)
    xs, ys = zip(*points.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
