"""Project actual edge fractions and reuse the parent's exact outlined letters."""

import hashlib
import itertools
import json
import math
import xml.etree.ElementTree as ET
from copy import deepcopy
from importlib.resources import files

from ..core.errors import ContentPlanError
from ..triangles.general.angle_label_positions import _position
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.right.construction_svg import _line, _tag
from .distance_sources import source_bytes

TEMPLATE_SHA256 = "4ce25fb0350e2b7e95edbe07626359a94eca0f0b1f8f09b5db194fdb6f26daee"


def template():
    raw = (
        files(__package__)
        .joinpath("assets/regular-triangle-cut-template.json")
        .read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA256:
        raise ContentPlanError("the reviewed triangular cut template changed")
    return json.loads(raw)


def _blend(a, b, fraction):
    return tuple(a[i] + fraction * (b[i] - a[i]) for i in (0, 1))


def scene(m, meta, scale=1):
    origin = meta["vertices"]["A"]
    vertices = {
        k: tuple(origin[i] + scale * (v[i] - origin[i]) for i in (0, 1))
        for k, v in meta["vertices"].items()
    }
    a, b, c, apex = (vertices[k] for k in ("A", "B", "C", "M"))
    vertices["O"] = tuple((a[i] + b[i] + c[i]) / 3 for i in (0, 1))
    t, r = float(m.q["AD"] / m.q["a"]), float(m.q["fraction"])
    vertices.update(
        D=_blend(a, c, t),
        E=_blend(a, b, t),
        L=_blend(a, apex, r),
        K=_blend(a, vertices["O"], r),
    )
    if m.symbols["section_foot"] == "H":
        vertices["H"] = _blend(vertices["D"], vertices["E"], 0.5)
    helpers = [vertices[k] for k in ("K", "O", "H") if k in vertices]
    if any(math.dist(p, q) < 2 for p, q in itertools.combinations(helpers, 2)):
        raise ContentPlanError(
            "the distinct auxiliary points cannot be distinguished in this projection"
        )
    return vertices


def _letters(root, vertices, meta):
    original = ET.fromstring(source_bytes(meta["source"]))
    auxiliary = ET.fromstring(source_bytes(meta["aux_source"]))
    boxes = []
    for name, point in vertices.items():
        if name == "H":
            group, box = deepcopy(auxiliary[meta["aux_index"]]), meta["aux_box"]
        else:
            group, box = (
                deepcopy(original[meta["glyph_indices"][name]]),
                meta["glyph_boxes"][name],
            )
        x, y, w, h = box
        dx, dy = meta["offsets"][name]
        preferred = (point[0] + dx - w / 2, point[1] + dy - h / 2)
        nx, ny = _position(root, point, w, h, boxes, preferred, max_distance=22)
        group.set("id", "label-" + name)
        group.set("transform", f"translate({nx - x:.8f} {ny - y:.8f})")
        root.append(group)
        boxes.append((nx, ny, w, h))
    return boxes


def _frame(m, meta, scale):
    vertices = scene(m, meta, scale)
    root = ET.Element(
        _tag("svg"),
        {"viewBox": "0 0 226.1742 196.0687", "data-projection-scale": str(scale)},
    )
    black = {
        "fill": "none",
        "stroke": "#0D0F0F",
        "stroke-width": "0.75",
        "stroke-linecap": "round",
        "stroke-linejoin": "round",
    }
    for a, b in (("A", "C"), ("A", "O"), ("M", "O"), ("L", "K")):
        _line(
            root,
            vertices[a],
            vertices[b],
            black | {"stroke-dasharray": "7.5 3"},
            a + "-" + b,
        )
    for a, b in (("A", "B"), ("B", "C"), ("M", "A"), ("M", "B"), ("M", "C")):
        _line(root, vertices[a], vertices[b], black, a + "-" + b)
    blue = black | {"stroke": "#143B8F"}
    for a, b, dashed in (("L", "E", False), ("L", "D", True), ("D", "E", True)):
        _line(
            root,
            vertices[a],
            vertices[b],
            blue | ({"stroke-dasharray": "7.5 3"} if dashed else {}),
            a + "-" + b,
        )
    if "H" in vertices:
        _line(root, vertices["L"], vertices["H"], blue, "L-H")
        if m.q["AH"] > m.q["R"]:
            _line(
                root,
                vertices["O"],
                vertices["H"],
                black | {"stroke-dasharray": "7.5 3"},
                "O-H",
            )
    boxes = _letters(root, vertices, meta)
    return canvas_svg(root, boxes + [(x, y, 0, 0) for x, y in vertices.values()])


def render(m):
    if m.mode != "regular_triangle_general_cut_area":
        raise ContentPlanError(
            "the generated triangle diagram needs the general cut model"
        )
    meta = template()
    last_error = None
    for scale in (1, 1.5, 2, 3):
        try:
            return _frame(m, meta, scale)
        except ContentPlanError as exc:
            last_error = exc
    raise ContentPlanError(
        "the cut diagram needs a distinguishable projection"
    ) from last_error
