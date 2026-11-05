"""Reuse the existing outlined-glyph remapper on reviewed prism isometries."""

import xml.etree.ElementTree as ET
from types import SimpleNamespace

from ..core.errors import ContentPlanError
from ..triangles.general.simple_angle_figures import _remapped
from ..triangles.right.construction_svg import _tag
from .prism_sources import source_bytes


def render(template, mapping):
    root = ET.fromstring(source_bytes(template["source"]))
    if template["flatten_outer"]:
        containers = [n for n in root if n.tag == _tag("g")]
        if len(containers) != 1 or containers[0].attrib:
            raise ContentPlanError("the reviewed cube lettering container changed")
        container = containers[0]
        index = list(root).index(container)
        for child in list(container):
            root.insert(index, child)
            index += 1
        root.remove(container)
    groups = [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != len(template["names"]) or len(groups) != len(template["boxes"]):
        raise ContentPlanError("the reviewed prism glyph layout changed")
    for group, box in zip(groups, template["boxes"]):
        x, y, w, h = box
        group.insert(
            0,
            ET.Element(
                _tag("rect"),
                {
                    "x": str(x),
                    "y": str(y),
                    "width": str(w),
                    "height": str(h),
                    "fill": "none",
                    "stroke": "none",
                },
            ),
        )
    transform = SimpleNamespace(name=lambda name: mapping.get(name, name))
    return _remapped(transform, ET.tostring(root), names=tuple(template["names"]))
