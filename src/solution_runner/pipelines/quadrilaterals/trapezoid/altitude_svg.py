"""Draw true right or oblique trapezoids, including overhanging upper vertices."""

import math
import xml.etree.ElementTree as ET
from types import SimpleNamespace

from ...core.errors import ContentPlanError
from ...triangles.general.height_area_svg import _extension
from ...triangles.isosceles.basic_figures import canvas_svg
from ...triangles.isosceles.side_altitude_svg import _corner, _style
from ...triangles.right.construction_svg import _line, _tag
from ..parallelogram.quantity_svg import _labels as merged_labels
from .isosceles_svg import _labels
from .quantity_sources import source_bytes

RIGHT_BARE = "9e4b66d6-e7a7-4734-bc73-0e8776d5511e"
RIGHT_HEIGHT = "430c4b07-05ce-48ae-bb19-d627292be3ab"
SIDE_BARE = "5f0e1c64-5dcf-4fff-a38b-dcc047ec2a55"
SIDE_HEIGHT = "9980f325-ad01-49c6-b594-4e9b42f08e96"
ANGLE_BARE = "d4486391-77ae-402d-abd1-75b98891adec"
ANGLE_HEIGHT = "ef5e7267-3207-4fa4-9339-efd4e38b9cb4"
PAIRS = {
    "right_area": (RIGHT_BARE, RIGHT_HEIGHT),
    "right_angle": (RIGHT_BARE, RIGHT_HEIGHT),
    "side_area": (SIDE_BARE, SIDE_HEIGHT),
    "side_angle": (ANGLE_BARE, ANGLE_HEIGHT),
}


def points(m):
    small, large, height, offset = map(float, (m.small, m.large, m.height, m.offset))
    p = {
        "A": (0, height),
        "B": (offset, 0),
        "C": (offset + small, 0),
        "D": (large, height),
        "H": (small if m.right else offset, height),
    }
    xs, ys = zip(*p.values())
    extent = max(max(xs) - min(xs), max(ys) - min(ys))
    if not math.isfinite(extent) or extent <= 0:
        raise ContentPlanError("the trapezoid geometry exceeds SVG precision")
    scale = 260 / extent
    if min(small, large - small, height) * scale < 0.01:
        raise ContentPlanError("distinct trapezoid vertices collapse at SVG precision")
    return {
        name: (12 + (x - min(xs)) * scale, 12 + y * scale) for name, (x, y) in p.items()
    }


def figure_svg(m, source):
    pair = PAIRS[m.mode]
    if source not in pair:
        raise ContentPlanError("the trapezoid drawing style differs from its method")
    detailed = source == pair[1]
    original = ET.fromstring(source_bytes(source))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    names = "ABCDH" if detailed else "ABCD"
    if len(groups) != len(names):
        raise ContentPlanError("the audited trapezoid lettering changed")
    glyphs = dict(zip(names, groups))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    p = points(m)
    for edge in ("AB", "BC", "CD", "DA"):
        _line(root, p[edge[0]], p[edge[1]], black, "side-" + edge)
    if detailed:
        blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
        start = "C" if m.right else "B"
        _extension(root, p, "AD", "H", black)
        _line(root, p[start], p["H"], blue, "height-" + start + "H")
        vertex = "D" if p["D"][0] > p["H"][0] + 1e-6 else "A"
        size = min(
            7.688,
            0.35 * math.dist(p[start], p["H"]),
            0.35 * math.dist(p[vertex], p["H"]),
        )
        _corner(root, p["H"], p[start], p[vertex], blue, "right-H", size=size)
    labelled = {name: p[name] for name in names}
    if detailed and math.dist(p["H"], p["D"]) < 1e-6:
        frame = SimpleNamespace(mode="altitude", name=lambda name: name, sine=m.sine)
        boxes = merged_labels(root, glyphs, frame, labelled, black)
    else:
        boxes = _labels(root, glyphs, labelled)
    xs, ys = zip(*p.values())
    root.set("viewBox", f"{min(xs)} {min(ys)} {max(xs) - min(xs)} {max(ys) - min(ys)}")
    return canvas_svg(root, boxes)
