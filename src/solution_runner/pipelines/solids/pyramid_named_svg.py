"""Place an existing outlined letter at one reviewed midpoint or center label."""

import xml.etree.ElementTree as ET
from copy import deepcopy

from ..core.errors import ContentPlanError
from ..triangles.isosceles.basic_figures import canvas_svg
from ..triangles.right.construction_svg import _tag
from .pyramid_sources import DATA, source_bytes


def _glyph(root, source, name):
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    layout = DATA["glyphs"][source]
    if len(groups) != len(layout) or name not in layout:
        raise ContentPlanError("the reviewed pyramid glyph layout changed")
    item = layout[name]
    return groups[item["index"]], item["box"]


def render(source, old, donor, name):
    root = ET.fromstring(source_bytes(source))
    previous, box = _glyph(root, source, old)
    borrowed, bounds = _glyph(ET.fromstring(source_bytes(donor)), donor, name)
    x, y, w, h = box
    bx, by, bw, bh = bounds
    baseline = y + h
    if old == "Q":
        baseline -= h - DATA["glyphs"][source]["S"]["box"][3]
    left = x + (w - bw) / 2
    top = baseline - bh
    replacement = deepcopy(borrowed)
    replacement.set("id", "label-" + name)
    replacement.set("transform", f"translate({left - bx:.6f} {top - by:.6f})")
    root.remove(previous)
    root.append(replacement)
    return canvas_svg(root, [(left, top, bw, bh)])
