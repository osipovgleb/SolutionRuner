"""Reuse audited unnumbered triangles by topology, with exact geometry when needed."""

import gzip
import hashlib
import math
import xml.etree.ElementTree as ET
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..right.construction_svg import _bounds, _line, _tag
from .area_model import read_question
from .basic_figures import canvas_svg
from .planner import _section
from .side_altitude_figures import _identity, condition_changes
from .side_altitude_svg import _place, _style

ACUTE = "f2040352-168b-4dfd-953c-da0f433aba13"
NARROW = "ec6d80b8-770c-4029-a726-58964413be69"
OBTUSE = "53d60821-5303-4fb4-a220-23a0833effe4"
KEY = "isosceles_area_condition"
_HASHES = {
    ACUTE: "6d21a70f1a8761149b9c9e2830c9d86f589d14dbb64997f7fe6d5d7c3f66bb21",
    NARROW: "4069b52b9f721e3f30248d5081280626d6ea632ef22e16eb44068ea12202fdff",
    OBTUSE: "daeb77841935c82ced156c580c71a077deb67d06747d4093e1c971e2110a5648",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the area diagram source needs review")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the reviewed area diagram changed")
    return raw


def triangle_svg(model):
    original = ET.fromstring(source_bytes(ACUTE))
    glyphs = dict(zip("ABC", original.findall(_tag("g"))))
    root = ET.Element(_tag("svg"), dict(original.attrib))
    left, right, bottom = 15.0321, 119.9139, 117.2406
    height = float(model.height / model.base) * (right - left)
    if not math.isfinite(height) or height <= 0:
        raise ContentPlanError(
            "the exact area triangle must have a finite positive height"
        )
    p, q, r = (left, bottom), (right, bottom), ((left + right) / 2, bottom - height)
    black = _style(original.find(_tag("polygon")))
    blue = _style(original.find(_tag("line")))
    for name, a, b in [("base", p, q), ("side-left", p, r), ("side-right", q, r)]:
        _line(root, a, b, black, name)
    for name, a in [("left", p), ("right", q)]:
        dx, dy = r[0] - a[0], r[1] - a[1]
        length = math.hypot(dx, dy)
        middle = ((a[0] + r[0]) / 2, (a[1] + r[1]) / 2)
        u = (-3.134 * dy / length, 3.134 * dx / length)
        _line(
            root,
            (middle[0] - u[0], middle[1] - u[1]),
            (middle[0] + u[0], middle[1] + u[1]),
            blue,
            "equal-" + name,
        )
    ends = sorted(set("ABC") - {model.apex})
    boxes = []
    for name, point in [(ends[0], p), (ends[1], q), (model.apex, r)]:
        _, _, w, h = _bounds(glyphs[name])
        x = point[0] - w if point == p else point[0] if point == q else point[0] - w / 2
        y = point[1] + 1 if point in (p, q) else point[1] - h - 1
        _place(root, glyphs, name, x, y, boxes)
    root.set("viewBox", f"{left} {r[1]} {right - left} {height}")
    return canvas_svg(root, boxes)


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized area content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) > 1
        or any(not isinstance(a, dict) for a in assets)
    ):
        raise ContentPlanError("at most one reviewed area condition image is supported")
    current = assets[0] if assets else {}
    key = current.get("asset_key")
    identifier = current.get("asset_id", "")
    if current and (
        key not in {"image_1", KEY}
        or not isinstance(identifier, str)
        or not identifier
        or current.get("kind") != "ordinary_image"
        or current.get("url") != "/assets/" + identifier
        or (key == "image_1" and identifier not in _HASHES)
    ):
        raise ContentPlanError("the area image metadata differs from a reviewed source")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete area condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) != len(assets) or (
        images
        and (
            images[0].get("data-asset-key") != key
            or images[0].get("data-asset-id") != identifier
        )
    ):
        raise ContentPlanError("the area condition image differs from its metadata")
    if images:
        images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    if model.topology is None:
        raise ContentPlanError("the area diagram topology must be determined exactly")
    if model.apex != "C" or model.topology == 0:
        return model, current, condition, KEY, ACUTE, spec(KEY, triangle_svg(model))
    compatible = {ACUTE, NARROW} if model.topology == 1 else {OBTUSE}
    source = (
        identifier
        if key == "image_1" and identifier in compatible
        else ACUTE
        if model.topology == 1
        else OBTUSE
    )
    source_bytes(source)
    return model, current, condition, "image_1", source, None


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, current, condition, key, source, diagram = selection(context)
    identifier, url = _identity(key, source, diagram, generated)
    return model, condition_changes(context, condition, current, key, identifier, url)
