"""Draw the actual two-altitude geometry using the parent's strokes and glyphs."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..isosceles.basic_figures import canvas_svg
from ..isosceles.side_altitude_svg import _corner, _place, _style
from ..right.construction_svg import _bounds, _line, _tag


def _extension(root, points, side, foot, style):
    p, q, h = (points[n] for n in (side[0], side[1], foot))
    v = (q[0] - p[0], q[1] - p[1])
    t = ((h[0] - p[0]) * v[0] + (h[1] - p[1]) * v[1]) / sum(x * x for x in v)
    if t < -1e-8 or t > 1 + 1e-8:
        _line(
            root,
            p if t < 0 else q,
            h,
            style | {"stroke-dasharray": "4 4"},
            "extension-" + foot,
        )


def _clear(x, y, width, height, boxes, role):
    for _ in range(len(boxes) + 1):
        overlaps = [
            (bx, by, bw, bh)
            for bx, by, bw, bh in boxes
            if x < bx + bw + 2
            and x + width + 2 > bx
            and y < by + bh + 2
            and y + height + 2 > by
        ]
        if not overlaps:
            break
        if role in {"C", "K"}:
            x = max(bx + bw + 3 for bx, by, bw, bh in overlaps)
        elif role == "H":
            x = min(bx - width - 3 for bx, by, bw, bh in overlaps)
        else:
            y = min(by - height - 3 for bx, by, bw, bh in overlaps)
    return x, y


def _labels(root, glyphs, points, black):
    groups = []
    for name, point in points.items():
        shared = next((g for g in groups if math.dist(g[0], point) < 1e-6), None)
        if shared is None:
            groups.append((point, [name]))
        else:
            shared[1].append(name)
    boxes = []
    for (x, y), names in groups:
        widths = [_bounds(glyphs[n])[2] for n in names]
        height = max(_bounds(glyphs[n])[3] for n in names)
        width = sum(widths) + 10 * (len(names) - 1)
        first = names[0]
        x, y = {
            "A": (x - width - 2, y + 2),
            "C": (x - width / 2, y + 2),
            "K": (x + 3, y - height / 2),
            "H": (x - width - 3, y - height - 1),
            "B": (x - width / 2, y - height - 2),
        }[first]
        x, y = _clear(x, y, width, height, boxes, first)
        for index, name in enumerate(names):
            _place(root, glyphs, name, x, y, boxes)
            x += widths[index]
            if index < len(names) - 1:
                for dy in (-1.5, 1.5):
                    _line(
                        root,
                        (x + 2, y + height / 2 + dy),
                        (x + 8, y + height / 2 + dy),
                        black,
                        f"equal-{first}-{index}-{dy}",
                    )
                x += 10
    return boxes


def height_svg(model, raw):
    original = ET.fromstring(raw)
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 5:
        raise ContentPlanError("the audited two-height lettering changed")
    glyphs = dict(zip("ABCHK", groups))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    cyan = _style(next(e for e in lines if e.get("stroke") == "#007EA5"))
    coords = {k: tuple(float(v) for v in p) for k, p in model.points.items()}
    scale = 160 / max(
        float(model.a), float(model.b), math.dist(coords["A"], coords["C"])
    )
    points = {k: (12 + x * scale, 120 + y * scale) for k, (x, y) in coords.items()}
    root = ET.Element(_tag("svg"), dict(original.attrib))
    for side in ("AB", "BC", "CA"):
        _line(root, points[side[0]], points[side[1]], black, "side-" + side)
    for side, start, foot, style in [("AB", "C", "H", blue), ("BC", "A", "K", cyan)]:
        _extension(root, points, side, foot, black)
        _line(root, points[start], points[foot], style, "altitude-" + foot)
        end = max(side, key=lambda n: math.dist(points[n], points[foot]))
        _corner(root, points[foot], points[start], points[end], style, "right-" + foot)
    boxes = _labels(root, glyphs, points, black)
    xs, ys = zip(*points.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
