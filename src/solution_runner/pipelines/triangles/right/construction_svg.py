"""Adapt audited vector lettering and strokes for reversed or coincident rays."""

import math
import xml.etree.ElementTree as ET
from copy import deepcopy

from ...core.errors import ContentPlanError
from .altitude_parent import _source
from .construction_angles import SOURCES

SOURCE_HASHES = {
    SOURCES["HD"]: "920a33d21d6179d4213b79efebe5022cfadc0caeb2eeea8c0973be92107461ea",
    SOURCES["HM"]: "11164bec093cbf0659c0bc18ba030900b233d208169bc1be32d9f99c00f32650",
    SOURCES["DM"]: "662cf51150d96b55b6f489b7ec1c64fcc43b87285aafa624579ba5780d02be2e",
}
_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def _tag(name):
    return "{" + _NS + "}" + name


def _xy(element, end):
    return tuple(float(element.get(axis + str(end))) for axis in ("x", "y"))


def _rect(group):
    return next(group.iter(_tag("rect")))


def _bounds(group):
    r = _rect(group)
    return tuple(float(r.get(k, "0")) for k in ("x", "y", "width", "height"))


def _template(pair):
    root = ET.fromstring(_source(SOURCES[pair], sources=SOURCE_HASHES))
    lines = root.findall(_tag("line"))
    sides = [e for e in lines if e.get("stroke") == "#0D0F0F"]
    baseline = min(sides, key=lambda e: abs(_xy(e, 1)[1] - _xy(e, 2)[1]))
    a, b = sorted((_xy(baseline, 1), _xy(baseline, 2)))
    rays = sorted((e for e in lines if e not in sides), key=lambda e: _xy(e, 2)[0])
    c = _xy(rays[0], 1)
    roles = {"HD": ("D", "H"), "HM": ("M", "H"), "DM": ("M", "D")}[pair]
    points = {"A": a, "B": b, "C": c} | dict(zip(roles, (_xy(e, 2) for e in rays)))
    letters = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(letters) != 5 or len(rays) != 2:
        raise ContentPlanError("the audited construction vector layout changed")
    upper = min(letters, key=lambda g: _bounds(g)[1])
    lower = sorted((g for g in letters if g is not upper), key=lambda g: _bounds(g)[0])
    glyphs = {"C": upper, "A": lower[0], "B": lower[-1]} | dict(zip(roles, lower[1:-1]))
    styles = {
        role: {k: v for k, v in ray.attrib.items() if k not in {"x1", "x2", "y1", "y2"}}
        for role, ray in zip(roles, rays)
    }
    black = {
        k: v for k, v in baseline.attrib.items() if k not in {"x1", "x2", "y1", "y2"}
    }
    return root, points, glyphs, styles, black


def _number(value):
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def _line(root, p, q, style, identifier):
    ET.SubElement(
        root,
        _tag("line"),
        style
        | {
            "id": identifier,
            "x1": _number(p[0]),
            "y1": _number(p[1]),
            "x2": _number(q[0]),
            "y2": _number(q[1]),
        },
    )


def _glyph(root, glyph, name, dx, dy):
    result = deepcopy(glyph)
    result.set("id", "label-" + name)
    result.set("transform", "translate(" + _number(dx) + " " + _number(dy) + ")")
    root.append(result)


def _coincident_labels(root, glyphs, points, old_points, style):
    roles = tuple(name for name in old_points if name not in {"A", "B", "C"})
    x, y = points[roles[0]]
    widths = [_bounds(glyphs[role])[2] for role in roles]
    equal_width, gap = 7, 2
    cursor = x - (sum(widths) + equal_width + 2 * gap) / 2
    for index, role in enumerate(roles):
        bx, _, width, height = _bounds(glyphs[role])
        _glyph(root, glyphs[role], role, cursor - bx, y - old_points["A"][1])
        cursor += width
        if index == 0:
            baseline = y + height * 0.6
            for row in (-1.5, 1.5):
                _line(
                    root,
                    (cursor + gap, baseline + row),
                    (cursor + gap + equal_width, baseline + row),
                    style,
                    "label-equal-" + str(row),
                )
            cursor += equal_width + 2 * gap


def _points(old_points, topology):
    a, b = old_points["A"], old_points["B"]
    base = a[1]
    length = b[0] - a[0]
    if topology == 0:
        length = min(length, 2 * (base - 24))
    beta = math.radians(45 if topology == 0 else 24)
    c = (
        a[0] + length * math.sin(beta) ** 2,
        base - length * math.sin(beta) * math.cos(beta),
    )
    return {
        "A": a,
        "B": (a[0] + length, base),
        "C": c,
        "H": (c[0], base),
        "M": (a[0] + length / 2, base),
        "D": (a[0] + length * math.tan(beta) / (1 + math.tan(beta)), base),
    }


def _right_markers(root, points, styles):
    c = points["C"]
    base = points["A"][1]
    roles = tuple(styles)
    marker_style = next(
        style for style in styles.values() if style["stroke"] == "#143B8F"
    )
    u, v = ((points[n][0] - c[0], points[n][1] - c[1]) for n in ("A", "B"))
    u, v = (
        tuple(7.5 * q / math.hypot(*u) for q in u),
        tuple(7.5 * q / math.hypot(*v) for q in v),
    )
    corners = [
        (c[0] + u[0], c[1] + u[1]),
        (c[0] + u[0] + v[0], c[1] + u[1] + v[1]),
        (c[0] + v[0], c[1] + v[1]),
    ]
    ET.SubElement(
        root,
        _tag("polyline"),
        marker_style
        | {
            "id": "right-C",
            "points": " ".join(_number(x) + "," + _number(y) for x, y in corners),
        },
    )
    if "H" in roles:
        h = points["H"]
        ET.SubElement(
            root,
            _tag("polyline"),
            marker_style
            | {
                "id": "right-H",
                "points": " ".join(
                    _number(x) + "," + _number(y)
                    for x, y in (
                        (h[0] + 7.5, base),
                        (h[0] + 7.5, base - 7.5),
                        (h[0], base - 7.5),
                    )
                ),
            },
        )


def figure_svg(pair, topology):
    if pair not in SOURCES or topology not in {-1, 0}:
        raise ContentPlanError(
            "only reversed and coincident constructions need a new SVG"
        )
    original, old_points, glyphs, styles, black = _template(pair)
    root = ET.Element(_tag("svg"), dict(original.attrib))
    points = _points(old_points, topology)
    base = points["A"][1]
    c = points["C"]
    for side in ("AC", "CB", "AB"):
        _line(root, points[side[0]], points[side[1]], black, "side-" + side)
    roles = tuple(styles)
    if topology == 0:
        role = "H" if "H" in roles else "D"
        _line(root, c, points[role], styles[role], "ray-" + "-".join(roles))
    else:
        for role in roles:
            _line(root, c, points[role], styles[role], "ray-" + role)
    _right_markers(root, points, styles)
    for name in ("A", "B", "C"):
        _glyph(
            root,
            glyphs[name],
            name,
            points[name][0] - old_points[name][0],
            points[name][1] - old_points[name][1],
        )
    if topology == 0:
        _coincident_labels(root, glyphs, points, old_points, black)
    else:
        for name in roles:
            bx, _, width, _ = _bounds(glyphs[name])
            offset = bx - old_points[name][0]
            new_x = points[name][0] - offset - width
            _glyph(root, glyphs[name], name, new_x - bx, base - old_points["A"][1])
    return ET.tostring(root, encoding="unicode")
