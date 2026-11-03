"""Reuse compatible vertex-altitude sources and the shared remapped/zero drawings."""

import gzip
import hashlib
import xml.etree.ElementTree as ET
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from .planner import _section
from .side_altitude_figures import _identity, condition_changes
from .side_altitude_sources import FONT_SOURCE
from .side_altitude_sources import source_bytes as font_bytes
from .side_altitude_svg import remapped_svg, zero_svg
from .vertex_altitude_model import read_question

ACUTE = "31121513-7af2-4c56-9add-d6348bb53635"
OBTUSE = "b2c2571f-216f-4c6c-9673-e6eb53984d9c"
KEY = "vertex_altitude_condition"
_HASHES = {
    ACUTE: "50f0738b204663c5e419d7509ebc3ad606244699d0dcc20e8dbf8879c1b30c8b",
    OBTUSE: "e5f853d32a74c72181c638b841419b8395b7827d19fc4a1665fbeda95c39763f",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the vertex-altitude image needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited vertex-altitude source changed")
    return raw


def _drawing(model):
    if model.topology == 0:
        root = ET.fromstring(zero_svg(model, font_bytes(FONT_SOURCE), False))
        for element in list(root):
            if element.get("id") in {"angle-P", "angle-Q"}:
                root.remove(element)
        return KEY, ACUTE, spec(KEY, ET.tostring(root, encoding="unicode"))
    source = ACUTE if model.topology < 0 else OBTUSE
    raw = source_bytes(source)
    if (model.vertex, model.other_base_vertex, model.apex) == ("A", "B", "C"):
        return "image_1", source, None
    return KEY, source, spec(KEY, remapped_svg(model, raw, False))


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError(
            "schema-v3 normalized vertex-altitude content is required"
        )
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError(
            "one reviewed vertex-altitude condition asset is required"
        )
    current = assets[0]
    key = current.get("asset_key")
    identifier = current.get("asset_id")
    if (
        key not in {"image_1", KEY}
        or not isinstance(identifier, str)
        or not identifier
        or current.get("kind") != "ordinary_image"
        or current.get("url") != "/assets/" + identifier
    ):
        raise ContentPlanError("the vertex-altitude image metadata changed")
    if key == "image_1":
        source_bytes(identifier)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete vertex-altitude condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError(
            "the vertex-altitude condition image differs from its metadata"
        )
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    return model, current, condition, *_drawing(model)


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, current, condition, key, source, diagram = selection(context)
    identifier, url = _identity(key, source, diagram, generated)
    return model, condition_changes(context, condition, current, key, identifier, url)
