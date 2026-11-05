"""Paint the actual polyhedron with reviewed cube-edge and diagonal styles."""

import hashlib
import json
import xml.etree.ElementTree as ET
from importlib.resources import files

from ..core.errors import ContentPlanError
from ..triangles.right.construction_svg import _tag
from . import box_coordinates as c
from .box_svg import render_svg
from .polyhedron_sources import source_bytes

TEMPLATE_SHA = "cb98e0e9c2ca8a4f3937a33794f1f308ad692067a926b5d99131b803df608d12"


def edges(solid):
    return tuple(
        sorted(
            {
                tuple(sorted((a, b)))
                for face in solid.faces
                for a, b in zip(face, face[1:] + face[:1])
            }
        )
    )


def template(source):
    raw = files(__package__).joinpath("assets/polyhedron-templates.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != TEMPLATE_SHA:
        raise ContentPlanError("the reviewed polyhedron template changed")
    return json.loads(raw)[source]


def figure_svg(model, source):
    meta = template(source)
    root = ET.fromstring(source_bytes(source))
    for group in list(root.findall(_tag("g"))):
        if not list(group.iter(_tag("path"))):
            root.remove(group)
    for node in root.findall(_tag("path")):
        root.remove(node)
    for node in root.findall(_tag("line")):
        if node.get("stroke") in {"#000000", "#0D0F0F"}:
            node.attrib.update(meta["wire_style"])
    svg = render_svg(ET.tostring(root), meta, model.squares, edges(model.solid))
    root = ET.fromstring(svg)
    for node in root.findall(_tag("line")):
        if not node.get("id", "").startswith("helper-"):
            continue
        a, b = node.get("id").removeprefix("helper-").split("-")
        node.attrib.update(
            meta["cube_style"] if len(c.axes(a + b)) == 1 else meta["diagonal_style"]
        )
    return ET.tostring(root, encoding="unicode")
