"""Read marked lattice intersections without assuming a perfectly uniform export."""

from itertools import pairwise
from math import hypot
from statistics import mean, median
from xml.etree import ElementTree as ET

from ..core.errors import ContentPlanError

NS = "{http://www.w3.org/2000/svg}"
COLORS = ("#143B8F", "#007EA5")


def vertical(node):
    return abs(float(node.get("x1")) - float(node.get("x2"))) < 0.2


def horizontal(node):
    return abs(float(node.get("y1")) - float(node.get("y2"))) < 0.2


def grid_axis(values, origin, step, sign):
    groups = []
    for value in sorted(v for v in values if abs(v - origin) > step * 0.1):
        if groups and value - groups[-1][-1] < step * 0.1:
            groups[-1].append(value)
        else:
            groups.append([value])
    coordinates = sorted([mean(g) for g in groups] + [origin])
    if not all(0.85 < (b - a) / step < 1.15 for a, b in pairwise(coordinates)):
        raise ContentPlanError(
            "the inspected coordinate grid has a missing or ambiguous cell"
        )
    zero = coordinates.index(origin)
    return [(pixel, (index - zero) * sign) for index, pixel in enumerate(coordinates)]


def frame(root, *, grid_color="#ADAAAA"):
    if any(n.get("transform") for n in root.iter()):
        raise ContentPlanError("transformed linear graphs require separate inspection")
    lines = list(root.iter(NS + "line"))
    grid = [n for n in lines if n.get("stroke", "").upper() == grid_color]
    xs = sorted({float(n.get("x1")) for n in grid if vertical(n)})
    ys = sorted({float(n.get("y1")) for n in grid if horizontal(n)})
    if len(xs) < 4 or len(ys) < 4:
        raise ContentPlanError("a coordinate grid with unit labels is required")
    sx, sy = (
        median([b - a for a, b in pairwise(values) if b - a > 1]) for values in (xs, ys)
    )
    black = [
        n
        for n in lines
        if n.get("stroke", "").upper() in {"#000000", "#0D0F0F", "#231F20"}
        and not n.get("stroke-dasharray")
    ]
    vx = [
        n
        for n in black
        if vertical(n) and abs(float(n.get("y1")) - float(n.get("y2"))) > 3 * sy
    ]
    hy = [
        n
        for n in black
        if horizontal(n) and abs(float(n.get("x1")) - float(n.get("x2"))) > 3 * sx
    ]
    if len(vx) != 1 or len(hy) != 1:
        raise ContentPlanError("unique coordinate axes are required")
    ox = mean(float(vx[0].get(k)) for k in ("x1", "x2"))
    oy = mean(float(hy[0].get(k)) for k in ("y1", "y2"))
    return grid_axis(xs, ox, sx, 1), grid_axis(ys, oy, sy, -1), sx, sy


def snap(position, mapping, step):
    pixel, value = min(mapping, key=lambda p: abs(p[0] - position))
    if abs(pixel - position) >= step * 0.075:
        raise ContentPlanError(
            "a graph marker must identify an unambiguous lattice intersection"
        )
    return value


def marked_line(root, color, axes):
    markers = [
        n for n in root.iter(NS + "circle") if n.get("fill", "").upper() == color
    ]
    lines = [n for n in root.iter(NS + "line") if n.get("stroke", "").upper() == color]
    if len(markers) != 2 or len(lines) != 1:
        raise ContentPlanError(
            "each linear graph needs one straight line and two marked points"
        )
    xmap, ymap, sx, sy = axes
    x1, y1, x2, y2 = (float(lines[0].get(k)) for k in ("x1", "y1", "x2", "y2"))
    length = hypot(x2 - x1, y2 - y1)
    if length == 0:
        raise ContentPlanError("a graph line must be nondegenerate")
    points = []
    for marker in markers:
        x, y = float(marker.get("cx")), float(marker.get("cy"))
        distance = abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / length
        if distance > min(sx, sy) * 0.05:
            raise ContentPlanError(
                "a marked point must lie on its colored straight line"
            )
        points.append([snap(x, xmap, sx), snap(y, ymap, sy)])
    return {"color": color, "points": points}


def read(data):
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ContentPlanError("invalid linear-function SVG") from exc
    axes = frame(root)
    colors = {n.get("fill", "").upper() for n in root.iter(NS + "circle")}
    if not colors or not colors <= set(COLORS):
        raise ContentPlanError("only the inspected graph marker colors are supported")
    return [marked_line(root, color, axes) for color in COLORS if color in colors]
