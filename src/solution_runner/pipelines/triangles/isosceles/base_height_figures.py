"""Reuse the equilateral height source and adapt its geometry and lettering."""

import gzip
import hashlib
import math
import xml.etree.ElementTree as ET
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..right.construction_svg import _bounds, _line, _tag
from .base_height_model import read_question
from .basic_figures import canvas_svg
from .planner import _section
from .side_altitude_figures import _identity, condition_changes
from .side_altitude_svg import _place, _style

SOURCE = "01886f85-0399-4f0f-94f6-5fddcc03aeca"
KEY = "isosceles_base_height"
SHA256 = "a59fa95261e95bf3be5250c1ff84d916fd9361bbb8dcfd61f26fe6ce48dc6429"


def source_bytes():
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + SOURCE + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ContentPlanError("the audited base-height SVG changed")
    return raw


def height_svg(model):
    original = ET.fromstring(source_bytes())
    root = ET.Element(_tag("svg"), dict(original.attrib))
    glyphs = dict(zip("ABCH", original.findall(_tag("g"))))
    lines = original.findall(_tag("line"))
    black = _style(next(e for e in lines if e.get("stroke") == "#0D0F0F"))
    blue = _style(next(e for e in lines if e.get("stroke") == "#143B8F"))
    left, right, bottom = 13.562, 129.134, 116.959
    height = float(model.height / model.base) * (right - left)
    if not math.isfinite(height) or height <= 0:
        raise ContentPlanError(
            "the base-height drawing must remain finite and nondegenerate"
        )
    p, q = (left, bottom), (right, bottom)
    h = ((left + right) / 2, bottom)
    r = (h[0], bottom - height)
    for name, a, b, style in [
        ("base", p, q, black),
        ("side-left", p, r, black),
        ("side-right", q, r, black),
        ("height", r, h, blue),
    ]:
        _line(root, a, b, style, name)
    corner = min(7.689, height * 0.35, (right - left) * 0.1)
    _line(
        root, (h[0] - corner, h[1]), (h[0] - corner, h[1] - corner), blue, "right-H-1"
    )
    _line(
        root, (h[0] - corner, h[1] - corner), (h[0], h[1] - corner), blue, "right-H-2"
    )
    a, b = model.base_vertices
    boxes = []
    for name, point in [(a, p), (b, q), (model.vertex, r), ("H", h)]:
        _, _, width, tall = _bounds(glyphs[name])
        x = (
            point[0] - width
            if point == p
            else point[0]
            if point == q
            else point[0] - width / 2
        )
        y = point[1] - tall - 1 if point == r else point[1] + 1
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
        raise ContentPlanError("schema-v3 normalized base-height content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one reviewed base-height condition image is required")
    current = assets[0]
    key = current.get("asset_key")
    identifier = current.get("asset_id")
    if (
        key not in {"image_1", KEY}
        or not isinstance(identifier, str)
        or not identifier
        or current.get("kind") != "ordinary_image"
        or current.get("url") != "/assets/" + identifier
        or (key == "image_1" and identifier != SOURCE)
    ):
        raise ContentPlanError("the base-height diagram metadata changed")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete base-height condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError(
            "the base-height condition image differs from its metadata"
        )
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    source_bytes()
    if model.vertex == "C" and model.apex_angle < 90:
        return model, current, condition, "image_1", None
    return model, current, condition, KEY, spec(KEY, height_svg(model))


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, current, condition, key, diagram = selection(context)
    identifier, url = _identity(key, SOURCE, diagram, generated)
    return model, condition_changes(context, condition, current, key, identifier, url)
