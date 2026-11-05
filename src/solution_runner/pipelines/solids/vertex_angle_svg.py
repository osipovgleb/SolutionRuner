"""Adapt actual angle triangles with the shared spatial renderer and parent's marks."""

import hashlib
import json
import xml.etree.ElementTree as ET
from importlib.resources import files

from ..core.errors import ContentPlanError
from ..triangles.isosceles.angle_svg import _arc
from ..triangles.right.construction_svg import _tag
from . import box_svg
from .box_vertex_angle_model import segments
from .vertex_angle_sources import source_bytes

TEMPLATE_SHA = "f4de6ac53c76c9a8286696a7e3531b7cd25ad8abfdba428e9c8173d0fc9699b5"


def figure_svg(model, source, *, mark):
    raw = (
        files(__package__)
        .joinpath("assets/box-vertex-angle-templates.json")
        .read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA:
        raise ContentPlanError("the reviewed vertex-angle template changed")
    meta = json.loads(raw)[source]
    root = ET.fromstring(source_bytes(source))
    for path in root.findall(_tag("path")):
        root.remove(path)
    svg = box_svg.render_svg(ET.tostring(root), meta, model.squares, segments(model))
    if not mark:
        return svg
    root = ET.fromstring(svg)
    vertices = box_svg.layout(meta, segments(model))
    a, b, c = (vertices[v] for v in model.vertices)
    _arc(
        root,
        b,
        (a, c),
        7,
        {
            "fill": "none",
            "stroke": "#0D0F0F",
            "stroke-width": "0.75",
            "stroke-linecap": "round",
            "stroke-linejoin": "round",
        },
        "requested-angle",
    )
    return ET.tostring(root, encoding="unicode")
