"""Reuse the audited plain cosine-law figure and shared triangle geometry."""

import gzip
import hashlib
from importlib.resources import files

import sympy as sp
from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from .area_figures import ACUTE, OBTUSE, plain_triangle_svg
from .area_figures import source_bytes as area_source_bytes
from .cosine_model import read_question
from .planner import _section
from .side_altitude_figures import _identity, condition_changes

SOURCE = "a6e5f963-52f8-4755-b2dc-09073a0c9889"
KEY = "isosceles_cosine_condition"
SHA256 = "d4580ea18b30c9c2ba3423dfc682daa9cc5e1e06e2e7d03b40662b0e2767cd2d"


def source_bytes(source):
    if source in {ACUTE, OBTUSE}:
        return area_source_bytes(source)
    if source != SOURCE:
        raise ContentPlanError("the cosine-law diagram needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + SOURCE + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ContentPlanError("the audited cosine-law diagram changed")
    return raw


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized cosine content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one reviewed cosine-law condition image is required")
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
        raise ContentPlanError("the cosine-law image metadata changed")
    if key == "image_1":
        source_bytes(identifier)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete cosine-law condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError(
            "the cosine-law picture reference differs from its metadata"
        )
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    if model.apex != "C" or model.topology == 0:
        ratio = 1 / (2 * sp.tan(sp.pi * model.apex_angle / 360))
        return (
            model,
            current,
            condition,
            KEY,
            SOURCE,
            spec(KEY, plain_triangle_svg(model.apex, ratio)),
        )
    compatible = {SOURCE, OBTUSE} if model.topology == -1 else {ACUTE}
    source = (
        identifier
        if key == "image_1" and identifier in compatible
        else SOURCE
        if model.topology == -1
        else ACUTE
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
