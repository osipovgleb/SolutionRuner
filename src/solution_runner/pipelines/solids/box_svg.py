"""Draw reviewed box wireframes with actual helper segments and exact labels."""

import math
import xml.etree.ElementTree as ET

import sympy as sp

from ..core.errors import ContentPlanError
from ..triangles.general.angle_label_positions import _position
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.isosceles.side_altitude_svg import _style
from ..triangles.right.construction_svg import _line, _tag
from . import box_coordinates as c


def hidden(a, b, back):
    fixed = [i for i in range(3) if c.VERTICES[a][i] == c.VERTICES[b][i]]
    return not fixed or all(c.VERTICES[a][i] == c.VERTICES[back][i] for i in fixed)


def number_text(value):
    return (
        sp.sstr(sp.simplify(value))
        .replace("sqrt(", "√(")
        .replace("**", "^")
        .replace("*", "·")
    )


def _numbers(root, squares, meta, vertices, boxes):
    for label in meta["number_labels"]:
        axis = label["axis"]
        text = number_text(sp.sqrt(squares[axis]))
        x, y, w, h = label["box"]
        size = h / 0.67
        width = max(size * 0.5, len(text) * size * 0.55)
        center = (x + w / 2, y + h / 2)
        if "√" in text or "^" in text:
            h = max(h, size)
        edge = label["edge"]
        old_p, old_q = (meta["vertices"][n] for n in edge)
        p, q = (vertices[n] for n in edge)
        dx = (p[0] + q[0] - old_p[0] - old_q[0]) / 2
        dy = (p[1] + q[1] - old_p[1] - old_q[1]) / 2
        anchor = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        tx, ty = _position(
            root, anchor, width, h, boxes, (center[0] + dx - width / 2, y + dy)
        )
        node = ET.SubElement(
            root,
            _tag("text"),
            {
                "id": "length-" + label.get("id", str(axis)),
                "x": f"{tx + width / 2:.6f}",
                "y": f"{ty + h:.6f}",
                "font-family": "Times New Roman, serif",
                "font-size": f"{size:.6f}",
                "text-anchor": "middle",
                "fill": "#000000",
            },
        )
        node.text = text
        boxes.append((tx, ty, width, h))


def _letters(root, groups, meta, vertices):
    boxes = {}
    for name, box in meta["glyph_boxes"].items():
        x, y, w, h = box
        dx = vertices[name][0] - meta["vertices"][name][0]
        dy = vertices[name][1] - meta["vertices"][name][1]
        boxes[name] = (x + dx, y + dy, w, h)
    for name, index in meta["glyph_indices"].items():
        x, y, w, h = boxes[name]
        others = [box for other, box in boxes.items() if other != name]
        nx, ny = _position(root, vertices[name], w, h, others, (x, y))
        group = groups[index]
        group.set("id", "vertex-" + name)
        original = meta["glyph_boxes"][name]
        if (nx, ny) != tuple(original[:2]):
            group.set(
                "transform", f"translate({nx - original[0]:.6f} {ny - original[1]:.6f})"
            )
        boxes[name] = (nx, ny, w, h)
    return list(boxes.values())


def _clear(vertices, segments):
    for a, b in segments:
        p, q = vertices[a], vertices[b]
        v = (q[0] - p[0], q[1] - p[1])
        square = v[0] ** 2 + v[1] ** 2
        for name, r in vertices.items():
            if name in (a, b):
                continue
            t = ((r[0] - p[0]) * v[0] + (r[1] - p[1]) * v[1]) / square
            if 0 < t < 1 and math.dist(r, (p[0] + t * v[0], p[1] + t * v[1])) < 4.5:
                return False
    return True


def layout(meta, required):
    old = meta["vertices"]
    origin = old["A"]
    basis = [
        (old[name][0] - origin[0], old[name][1] - origin[1])
        for name in ("B", "D", "A_1")
    ]
    depth = next(i for i in (0, 1) if abs(basis[i][1]) > 1)
    for factor in (1, 1.5, 0.6, 2, 0.4):
        vectors = [
            (x, y * factor if i == depth else y) for i, (x, y) in enumerate(basis)
        ]
        vertices = {
            name: tuple(
                origin[j] + sum(point[i] * vectors[i][j] for i in range(3))
                for j in (0, 1)
            )
            for name, point in c.VERTICES.items()
        }
        if _clear(vertices, required):
            return vertices
    raise ContentPlanError(
        "the spatial projection cannot distinguish the requested segments"
    )


def _wireframe(root, vertices, back, style):
    names = list(c.VERTICES)
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            if len(c.axes(a + b)) != 1:
                continue
            edge_style = style | (
                {"stroke-dasharray": "7.5,3"} if hidden(a, b, back) else {}
            )
            _line(root, vertices[a], vertices[b], edge_style, "wire-" + a + "-" + b)


def render_svg(raw, meta, squares, segments):
    root = ET.fromstring(raw)
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    letters = set(meta["glyph_indices"].values())
    if len(groups) != len(letters) + len(meta["number_labels"]):
        raise ContentPlanError("the reviewed spatial lettering changed")
    for i, g in enumerate(groups):
        if i not in letters:
            root.remove(g)
    lines = root.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    colored = [e for e in lines if e.get("stroke") == "#143B8F"]
    blue_style = _style(colored[0]) if colored else black | {"stroke": "#143B8F"}
    for e in lines:
        root.remove(e)
    vertices = layout(meta, segments)
    _wireframe(root, vertices, meta["hidden_corner"], black)
    for a, b in segments:
        style = blue_style | (
            {"stroke-dasharray": "7.5,3"} if hidden(a, b, meta["hidden_corner"]) else {}
        )
        _line(root, vertices[a], vertices[b], style, "helper-" + a + "-" + b)
    boxes = _letters(root, groups, meta, vertices)
    _numbers(root, squares, meta, vertices, boxes)
    return canvas_svg(root, boxes + [(x, y, 0, 0) for x, y in vertices.values()])
