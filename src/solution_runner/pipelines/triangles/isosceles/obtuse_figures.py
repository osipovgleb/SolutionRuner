"""Repair the audited obtuse diagram canvas and adapt its actual vertex labels."""

import gzip
import hashlib
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from .basic_figures import uncrop_svg
from .obtuse_model import read_question
from .planner import _section
from .side_altitude_figures import _identity, condition_changes
from .side_altitude_svg import remapped_svg

SOURCE = "89c0f5f7-a4cf-4231-be40-994be7db21dd"
KEY = "obtuse_condition"
SHA256 = "8e0f2a858e46c3d4f8f6aea8bf2b649f33a1ec79e9e4c64ad3b227e5be66a6e1"


def source_bytes():
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + SOURCE + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise ContentPlanError("the audited obtuse source diagram changed")
    return raw


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized obtuse content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one reviewed obtuse condition asset is required")
    current = assets[0]
    key, identifier = current.get("asset_key"), current.get("asset_id")
    if (
        key not in {"image_1", KEY}
        or not isinstance(identifier, str)
        or not identifier
        or current.get("kind") != "ordinary_image"
        or current.get("url") != "/assets/" + identifier
        or (key == "image_1" and identifier != SOURCE)
    ):
        raise ContentPlanError("the obtuse condition asset identity changed")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete obtuse condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError("the obtuse condition figure differs from its metadata")
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    raw = source_bytes()
    svg = (
        uncrop_svg(raw)
        if (model.vertex, model.other_base_vertex, model.apex) == ("A", "B", "C")
        else remapped_svg(model, raw, False)
    )
    return model, current, condition, spec(KEY, svg)


def diagram_specs(context):
    return (selection(context)[3],)


def prepare(context, generated):
    model, current, condition, diagram = selection(context)
    identifier, url = _identity(KEY, SOURCE, diagram, generated)
    return model, condition_changes(context, condition, current, KEY, identifier, url)
