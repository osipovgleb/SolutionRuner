"""Reuse audited midline sources and relabel both cases together when needed."""

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
from .midline_model import read_question

SMALL = "52077366-ea3b-4894-9267-0842cd901fe6"
TOTAL = "3f8957dd-6a7f-467f-9ea1-0eeb12e56607"
SECOND = "e231e60a-910f-405d-93f0-5c6dd10a14c7"
TRAPEZOID = "bc968769-1284-4deb-9ce9-4505ae004525"
CONDITION_KEY = "midline_condition"
SOLUTION_KEY = "midline_second_case"
SOURCES = {"small": SMALL, "total": TOTAL, "trapezoid": TRAPEZOID}
_HASHES = {
    SMALL: "ef99e5efeec2cbb5934319131180cbd0d1ef98c5c5eb17bf2c96a7e3485cde95",
    TOTAL: "4574d5314e30d777b0d82d82752140657c54f11df45b4385eb42fd98f4b05767",
    SECOND: "d24aa2edd831699a10066fd93f5552590dde01684dd3e607abba2f5b94f6f4b8",
    TRAPEZOID: "0143e829530519602961ebada27de56e9d85dc2193c44ac8e0c9ecf9ac80d4bd",
}


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the midline source needs a mathematical audit")
    raw = gzip.decompress(
        files(__package__).joinpath("assets/" + source + ".svgz").read_bytes()
    )
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited midline SVG changed")
    return raw


def _remapped(model, source):
    original = ET.fromstring(source_bytes(source))
    groups = [g for g in original.findall(_tag("g")) if list(g.iter(_tag("path")))]
    if len(groups) != 5:
        raise ContentPlanError("the audited ABCDE midline lettering changed")
    glyphs = dict(zip("ABCDE", groups))
    root = deepcopy(original)
    for group in [g for g in root.findall(_tag("g")) if list(g.iter(_tag("path")))]:
        root.remove(group)
    boxes = []
    for role, target in glyphs.items():
        x, y, w, h = _bounds(target)
        desired = model.mapping[role]
        gw, gh = _bounds(glyphs[desired])[2:]
        _place(root, glyphs, desired, x + (w - gw) / 2, y + h - gh, boxes)
    return canvas_svg(root, boxes)


def _assets(content):
    assets = content.get("assets")
    if not isinstance(assets, list) or any(not isinstance(a, dict) for a in assets):
        raise ContentPlanError("midline assets must be a complete metadata list")
    by_key = {a.get("asset_key"): a for a in assets}
    if len(by_key) != len(assets) or set(by_key) - {
        "image_1",
        "image_2",
        CONDITION_KEY,
        SOLUTION_KEY,
    }:
        raise ContentPlanError("unreviewed or duplicate midline assets are present")
    if len(set(by_key) & {"image_1", CONDITION_KEY}) != 1:
        raise ContentPlanError("one primary midline figure is required")
    for key, asset in by_key.items():
        identifier = asset.get("asset_id")
        if (
            not isinstance(identifier, str)
            or not identifier
            or asset.get("kind") != "ordinary_image"
            or asset.get("url") != "/assets/" + identifier
        ):
            raise ContentPlanError("the midline asset metadata changed")
        if key == "image_1":
            if identifier not in SOURCES.values():
                raise ContentPlanError("the midline condition source is unreviewed")
            source_bytes(identifier)
        elif key == "image_2":
            if identifier != SECOND:
                raise ContentPlanError("the second midline case source is unreviewed")
            source_bytes(identifier)
    return by_key


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized midline content is required")
    assets = _assets(content)
    current = next(assets[k] for k in ("image_1", CONDITION_KEY) if k in assets)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete midline condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != current["asset_key"]
        or images[0].get("data-asset-id") != current["asset_id"]
    ):
        raise ContentPlanError("the midline condition figure differs from its metadata")
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), current["asset_id"])
    if model.mode != "total" and set(assets) & {"image_2", SOLUTION_KEY}:
        raise ContentPlanError("this midline method has no solution figure")
    source = SOURCES[model.mode]
    source_bytes(source)
    first = (
        spec(CONDITION_KEY, _remapped(model, source)) if model.vertex != "C" else None
    )
    second = (
        spec(SOLUTION_KEY, _remapped(model, SECOND))
        if model.mode == "total" and model.vertex != "C"
        else None
    )
    return model, current, condition, assets, first, second


def diagram_specs(context):
    return tuple(s for s in selection(context)[-2:] if s is not None)


def _solution_image(model, assets, diagram, generated):
    if model.mode != "total":
        return "", (), ()
    key = SOLUTION_KEY if diagram else "image_2"
    identifier, url = _identity(
        key, SECOND, diagram, tuple(g for g in generated if g.get("asset_key") == key)
    )
    soup = BeautifulSoup('<img alt=""/>', "html.parser")
    image = soup.img
    image.attrs.update(
        {
            "data-asset-key": key,
            "data-asset-id": identifier,
            "src": url,
            "data-transformation-target-id": "asset:" + key,
        }
    )
    changes = []
    if key not in assets or assets[key]["asset_id"] != identifier:
        changes.append(
            {
                "transformation_target_id": "asset:" + key,
                "operation": "rewrite" if key in assets else "add",
                "value": {
                    "asset_key": key,
                    "asset_id": identifier,
                    "url": url,
                    "kind": "ordinary_image",
                    "alt": "",
                    "position": 0,
                    "parent_target_id": "section:solution:1",
                    "html": str(image),
                },
            }
        )
    old_key = "image_2" if diagram else SOLUTION_KEY
    if old_key in assets:
        changes.append(
            {"transformation_target_id": "asset:" + old_key, "operation": "remove"}
        )
    return "<center>" + str(image) + "</center>", (key,), tuple(changes)


def prepare(context, generated):
    model, current, condition, assets, first, second = selection(context)
    expected_keys = {s["asset_key"] for s in (first, second) if s}
    if (
        len(generated) != len(expected_keys)
        or {g.get("asset_key") for g in generated} != expected_keys
    ):
        raise ContentPlanError("the generated midline figures do not match both cases")
    key = CONDITION_KEY if first else "image_1"
    identifier, url = _identity(
        key,
        SOURCES[model.mode],
        first,
        tuple(g for g in generated if g.get("asset_key") == key),
    )
    # The second-case image is managed below, independently of the condition.
    changes = tuple(
        t
        for t in condition_changes(context, condition, current, key, identifier, url)
        if t["transformation_target_id"] != "asset:image_2"
    )
    image, keys, solution_changes = _solution_image(model, assets, second, generated)
    return model, changes + solution_changes, image, keys
