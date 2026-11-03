"""Keep compatible angle diagrams and remap their original outlined lettering."""

import gzip
import hashlib
import xml.etree.ElementTree as ET
from copy import deepcopy
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.basic_figures import canvas_svg
from ..isosceles.planner import _section
from ..isosceles.side_altitude_figures import _identity, condition_changes
from ..isosceles.side_altitude_svg import _place
from ..right.construction_svg import _bounds, _tag
from .simple_angle_model import read_question

EXTERNAL = "acf0700e-c2d9-451b-b6b0-f04a2b718de1"
BISECTOR_BASE = "6fec46c1-abc5-4b85-86ec-08f4e76a8341"
BISECTOR_EXTERNAL = "a1e16fd0-1b72-4515-923b-482eaafaebdd"
SOURCES = {
    "external": EXTERNAL,
    "bisector_base": BISECTOR_BASE,
    "bisector_external": BISECTOR_EXTERNAL,
}
KEY = "simple_angle_condition"
_HASHES = {
    EXTERNAL: "24d0db05357700f712dc13640ef758cab9e0a655b3feefe91593b0f7e4b9c216",
    BISECTOR_BASE: "f7be3b4d2a5e646b890240d438f6723a095dc4bd36391679afdff9b164e215a2",
    BISECTOR_EXTERNAL: "2d5bbbcbb9f41f94e6426d9f4086a5bfe551070cdccffe85a4eaf9b8281a3fca",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the simple-angle diagram needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited simple-angle SVG changed")
    return raw


def _remapped(model, raw):
    original = ET.fromstring(raw)
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    names = "ABC" if model.mode == "external" else "ABCD"
    if len(groups) != len(names):
        raise ContentPlanError("the reviewed simple-angle lettering changed")
    glyphs = dict(zip(names, groups))
    root = deepcopy(original)
    for group in [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]:
        root.remove(group)
    boxes = []
    for role, target in glyphs.items():
        x, y, w, h = _bounds(target)
        desired = model.name(role)
        gw, gh = _bounds(glyphs[desired])[2:]
        _place(root, glyphs, desired, x + (w - gw) / 2, y + h - gh, boxes)
    return canvas_svg(root, boxes)


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized simple-angle content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one reviewed simple-angle condition figure is required")
    asset = assets[0]
    key, identifier = asset.get("asset_key"), asset.get("asset_id")
    if (
        key not in {"image_1", KEY}
        or not isinstance(identifier, str)
        or not identifier
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != "/assets/" + identifier
    ):
        raise ContentPlanError("the simple-angle diagram metadata changed")
    if key == "image_1":
        source_bytes(identifier)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete simple-angle condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError("the simple-angle condition image differs from metadata")
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    source = SOURCES[model.mode]
    raw = source_bytes(source)
    diagram = None if model.frame == "ABC" else spec(KEY, _remapped(model, raw))
    return model, asset, condition, source, diagram


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, asset, condition, source, diagram = selection(context)
    key = KEY if diagram else "image_1"
    identifier, url = _identity(key, source, diagram, generated)
    return model, condition_changes(context, condition, asset, key, identifier, url)
