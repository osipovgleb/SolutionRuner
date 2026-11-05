"""Draw the actual section diagonals using the parent's shared box renderer."""

import hashlib
import json
import xml.etree.ElementTree as ET
from importlib.resources import files

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _tag
from . import box_svg, line_angle_parent
from .box_section_model import segments
from .box_section_sources import source_bytes
from .line_angle_sources import SOURCE

OBLIQUE = "fa12724f-ab48-4029-b612-8821c8f857d1"
TEMPLATE_SHA = "4c3898f14973cb45c2c27b574c5c91b3e95737f2da01087682cf7cb8267d6e57"


def template(source):
    filename, digest = (
        ("box-line-angle-template.json", line_angle_parent.TEMPLATE_SHA)
        if source == SOURCE
        else ("box-section-template.json", TEMPLATE_SHA)
    )
    raw = files(__package__).joinpath("assets/" + filename).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ContentPlanError("the reviewed box-section template changed")
    return json.loads(raw)[source]


def helpers(m, source):
    pairs = segments(m)
    return (
        pairs
        if source == SOURCE
        else tuple(sorted((*pairs, tuple(sorted(m.vertices[2:])))))
    )


def figure_svg(m, source):
    root = ET.fromstring(source_bytes(source))
    for group in list(root.findall(_tag("g"))):
        if not list(group.iter(_tag("path"))):
            root.remove(group)
    for node in root.findall(_tag("line")):
        if node.get("stroke") == "#000000":
            node.set("stroke", "#0D0F0F")
    return box_svg.render_svg(
        ET.tostring(root), template(source), m.squares, helpers(m, source)
    )
