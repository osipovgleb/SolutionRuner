"""Reuse reviewed concurrent-bisector figures and their shared glyph remapper."""

import gzip
import hashlib
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ..isosceles.planner import _section
from ..isosceles.side_altitude_figures import _identity, condition_changes
from .incenter_model import read_question
from .simple_angle_figures import _remapped

BETWEEN = "2de5a758-29d7-4352-82d4-b3414e4f3287"
OBTUSE = "0455eddb-95c6-41c0-8218-6587753c672f"
FOOT = "57cc4c98-dfbc-4dd3-bd66-c0a2b7e35498"
SOURCES = {"between": BETWEEN, "foot": FOOT}
KEYS = {
    BETWEEN: "incenter_between_condition",
    OBTUSE: "incenter_obtuse_condition",
    FOOT: "incenter_foot_condition",
}
_HASHES = {
    BETWEEN: "d55d2f50c19323e0c4e284277524334bd22f8bac748d212945115d41eca70131",
    OBTUSE: "b6c1393b5f9873609f14c41173e39557f1a878406fd3aeb4192dcedfcd275ad6",
    FOOT: "55e400c1aaf01f296f94ca38b7b73c1f5901617fca0b6d956383e71532fea72b",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the incenter diagram needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited incenter SVG changed")
    return raw


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized incenter content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one reviewed incenter condition diagram is required")
    asset = assets[0]
    key, identifier = asset.get("asset_key"), asset.get("asset_id")
    if (
        key not in {"image_1", *KEYS.values()}
        or not isinstance(identifier, str)
        or not identifier
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != "/assets/" + identifier
    ):
        raise ContentPlanError("the incenter diagram metadata changed")
    source = (
        identifier if key == "image_1" else next(s for s, k in KEYS.items() if k == key)
    )
    raw = source_bytes(source)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete incenter condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError("the incenter condition image differs from its metadata")
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    if (model.mode == "foot") != (source == FOOT):
        raise ContentPlanError(
            "the source must depict the declared set of concurrent bisectors"
        )
    names = "ABCDEFO" if model.mode == "foot" else "ABCDEO"
    diagram = (
        None
        if model.frame == "ABC"
        else spec(KEYS[source], _remapped(model, raw, names))
    )
    return model, asset, condition, source, diagram


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, asset, condition, source, diagram = selection(context)
    key = diagram["asset_key"] if diagram else "image_1"
    identifier, url = _identity(key, source, diagram, generated)
    return model, condition_changes(context, condition, asset, key, identifier, url)
