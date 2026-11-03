"""Draw the coincident side altitude with the audited source's outlined lettering."""

import math
import xml.etree.ElementTree as ET

from ...core.errors import ContentPlanError
from ..right.construction_svg import _bounds, _glyph, _line, _tag
from .basic_figures import canvas_svg


def _lettering(root):
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 5:
        raise ContentPlanError("the reviewed five-letter isosceles source changed")
    c = min(groups, key=lambda g: _bounds(g)[1])
    remaining = [g for g in groups if g is not c]
    a = min(remaining, key=lambda g: _bounds(g)[0])
    b = max(remaining, key=lambda g: _bounds(g)[0])
    remaining = [g for g in remaining if g is not a and g is not b]
    k = max(remaining, key=lambda g: _bounds(g)[1])
    h = next(g for g in remaining if g is not k)
    return {"A": a, "B": b, "C": c, "H": h, "K": k}


def _style(line):
    return {
        k: v
        for k, v in line.attrib.items()
        if k
        in {
            "fill",
            "stroke",
            "stroke-width",
            "stroke-linecap",
            "stroke-linejoin",
            "stroke-miterlimit",
        }
    }


def _corner(root, o, p, q, style, name):
    u = (p[0] - o[0], p[1] - o[1])
    v = (q[0] - o[0], q[1] - o[1])
    u = tuple(7.688 * z / math.hypot(*u) for z in u)
    v = tuple(7.688 * z / math.hypot(*v) for z in v)
    points = [
        (o[0] + u[0], o[1] + u[1]),
        (o[0] + u[0] + v[0], o[1] + u[1] + v[1]),
        (o[0] + v[0], o[1] + v[1]),
    ]
    ET.SubElement(
        root,
        _tag("polyline"),
        style | {"id": name, "points": " ".join(f"{x:.6f},{y:.6f}" for x, y in points)},
    )


def _place(root, glyphs, name, x, y, boxes):
    bx, by, w, h = _bounds(glyphs[name])
    _glyph(root, glyphs[name], name, x - bx, y - by)
    boxes.append((x, y, w, h))


def _merged(root, glyphs, apex, point, black, boxes):
    first, second = glyphs[apex], glyphs["H"]
    w1, h1 = _bounds(first)[2:]
    w2, h2 = _bounds(second)[2:]
    x = point[0] - (w1 + w2 + 10) / 2
    bottom = point[1] - 4
    _place(root, glyphs, apex, x, bottom - h1, boxes)
    _place(root, glyphs, "H", x + w1 + 10, bottom - h2, boxes)
    for index, dy in enumerate((-1.5, 1.5)):
        _line(
            root,
            (x + w1 + 2, bottom - h2 * 0.45 + dy),
            (x + w1 + 8, bottom - h2 * 0.45 + dy),
            black,
            "merged-equal-" + str(index),
        )


def _ticks_and_arcs(root, p, q, r, black):
    for name, end in [("P", p), ("Q", q)]:
        dx, dy = r[0] - end[0], r[1] - end[1]
        norm = math.hypot(dx, dy)
        mid = ((r[0] + end[0]) / 2, (r[1] + end[1]) / 2)
        u = (-2.8 * dy / norm, 2.8 * dx / norm)
        _line(
            root,
            (mid[0] - u[0], mid[1] - u[1]),
            (mid[0] + u[0], mid[1] + u[1]),
            black,
            "equal-side-" + name,
        )
    radius = 7
    for name, start, end, sweep in [
        (
            "P",
            (p[0] + radius, p[1]),
            (p[0] + radius / math.sqrt(2), p[1] - radius / math.sqrt(2)),
            0,
        ),
        (
            "Q",
            (q[0] - radius, q[1]),
            (q[0] - radius / math.sqrt(2), q[1] - radius / math.sqrt(2)),
            1,
        ),
    ]:
        ET.SubElement(
            root,
            _tag("path"),
            black
            | {
                "id": "angle-" + name,
                "d": f"M{start[0]:.6f},{start[1]:.6f} A{radius},{radius} 0 0 {sweep} {end[0]:.6f},{end[1]:.6f}",
            },
        )


def zero_svg(model, raw, with_k):
    if model.topology != 0:
        raise ContentPlanError("a coincident-foot SVG requires a right apex")
    original = ET.fromstring(raw)
    glyphs = _lettering(original)
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    decoration = _style(
        next(e for e in original.findall(_tag("path")) if e.get("stroke") == "#000000")
    )
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    cyan = _style(next(e for e in lines if e.get("stroke") == "#007EA5"))
    baseline = next(
        e
        for e in lines
        if e.get("stroke") == "#0D0F0F"
        and abs(float(e.get("y1")) - float(e.get("y2"))) < 0.001
    )
    left, right = sorted((float(baseline.get("x1")), float(baseline.get("x2"))))
    y = float(baseline.get("y1"))
    p, q, r = (left, y), (right, y), ((left + right) / 2, y - (right - left) / 2)
    k = (r[0], y)
    root = ET.Element(_tag("svg"), dict(original.attrib))
    boxes = []
    _line(root, p, q, black, "base")
    _line(root, q, r, black, "side-Q")
    _line(root, p, r, blue, "side-P-height")
    _corner(root, r, p, q, blue, "right-H-apex")
    _ticks_and_arcs(root, p, q, r, decoration)
    for name, point, is_left in [
        (model.vertex, p, True),
        (model.other_base_vertex, q, False),
    ]:
        w = _bounds(glyphs[name])[2]
        _place(
            root,
            glyphs,
            name,
            point[0] - w + 2 if is_left else point[0] - 2,
            point[1] + 1,
            boxes,
        )
    _merged(root, glyphs, model.apex, r, decoration, boxes)
    if with_k:
        _line(root, r, k, cyan, "apex-altitude")
        _corner(root, k, r, q, cyan, "right-K")
        w = _bounds(glyphs["K"])[2]
        _place(root, glyphs, "K", k[0] - w / 2, k[1] + 1, boxes)
    root.set("viewBox", f"{left} {r[1]} {right - left} {y - r[1]}")
    return canvas_svg(root, boxes)


def remapped_svg(model, raw, with_k):
    """Keep a canonical audited construction and place its glyphs at actual vertices."""
    from copy import deepcopy

    original = ET.fromstring(raw)
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    names = "ABCHK" if with_k else "ABCH"
    if len(groups) != len(names):
        raise ContentPlanError("the canonical source lettering changed")
    glyphs = dict(zip(names, groups))
    mapping = {
        "A": model.vertex,
        "B": model.other_base_vertex,
        "C": model.apex,
        "H": "H",
        "K": "K",
    }
    root = deepcopy(original)
    copies = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    boxes = []
    for role, old in zip(names, copies):
        desired = mapping[role]
        target = glyphs[role]
        glyph = deepcopy(glyphs[desired])
        tx, ty, tw, th = _bounds(target)
        gx, gy, gw, gh = _bounds(glyph)
        dx, dy = tx + tw / 2 - gx - gw / 2, ty + th - gy - gh
        glyph.set("id", "label-" + desired)
        glyph.set("transform", f"translate({dx:.6f} {dy:.6f})")
        index = list(root).index(old)
        root.remove(old)
        root.insert(index, glyph)
        for rect in glyph.iter(_tag("rect")):
            boxes.append(
                (
                    float(rect.get("x", 0)) + dx,
                    float(rect.get("y", 0)) + dy,
                    float(rect.get("width")),
                    float(rect.get("height")),
                )
            )
    return canvas_svg(root, boxes)
