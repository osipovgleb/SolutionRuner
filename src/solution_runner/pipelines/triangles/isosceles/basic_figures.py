"""Reuse the reviewed isosceles figures and repair only the cropped SVG canvas."""

import gzip
import hashlib
import xml.etree.ElementTree as ET
from importlib.resources import files

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...word_problems.common import rewrite
from ..right.basic_parent import _targeted
from .basic_model import read_context

HEIGHT = "6c4f65f7-c74b-438a-8599-47ba154243ff"
BARE = "7436dcaa-d6da-4903-b3cc-f7a4f5edcc65"
RASTER = "743ecbb6-42b5-4ff9-a3d0-e575879f20fa"
GENERATED_KEY = "isosceles_condition"
_HASHES = {
    HEIGHT: "f0de183e36419444811ebecd1dbb965a280264531d10518181aa5a7e027b54d8",
    BARE: "7562a4996b766a4ad063d8a287f9c175bfeed895d0a775d08e9bca5fde04ec9c",
    RASTER: "2c8908b707393e0d3954707d4abcd5e0c731d9bb4dd71e0e1f829d7c002c7452",
}
_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", _NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")


def source_bytes(source):
    if source not in _HASHES:
        raise ContentPlanError("the isosceles figure needs a mathematical audit")
    extension = ".png" if source == RASTER else ".svgz"
    raw = files(__package__).joinpath("assets/" + source + extension).read_bytes()
    if extension == ".svgz":
        raw = gzip.decompress(raw)
    if hashlib.sha256(raw).hexdigest() != _HASHES[source]:
        raise ContentPlanError("the audited isosceles SVG changed")
    return raw


def uncropped_svg():
    root = ET.fromstring(source_bytes(BARE))
    x, y, width, height = map(float, root.get("viewBox").split())
    left, top, right, bottom = x, y, x + width, y + height
    for rect in root.iter("{" + _NS + "}rect"):
        rx, ry = float(rect.get("x", 0)), float(rect.get("y", 0))
        left, top = min(left, rx), min(top, ry)
        right, bottom = (
            max(right, rx + float(rect.get("width"))),
            max(bottom, ry + float(rect.get("height"))),
        )
    left, top, right, bottom = left - 2, top - 2, right + 2, bottom + 2
    box = " ".join(
        f"{v:.6f}".rstrip("0").rstrip(".")
        for v in (left, top, right - left, bottom - top)
    )
    root.set("viewBox", box)
    root.set("width", f"{right - left:.6f}px")
    root.set("height", f"{bottom - top:.6f}px")
    root.set("enable-background", "new " + box)
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context):
    model = read_context(context)
    content = context["normalized_content"]
    candidates = [
        a
        for a in content.get("assets", [])
        if a.get("asset_key") in {"image_1", GENERATED_KEY}
    ]
    if len(candidates) != 1:
        raise ContentPlanError("one audited primary isosceles figure is required")
    current = candidates[0]
    if current.get("asset_id") == BARE or current.get("asset_key") == GENERATED_KEY:
        if (model.function, model.given_kind) != ("tg", "base"):
            raise ContentPlanError(
                "the bare condition and separate height figure need the reviewed tangent method"
            )
        return (spec(GENERATED_KEY, uncropped_svg()),)
    if current.get("asset_id") not in {HEIGHT, RASTER}:
        raise ContentPlanError("the primary isosceles figure is not reviewed")
    return ()


def _assets(content):
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or not assets
        or any(not isinstance(a, dict) for a in assets)
    ):
        raise ContentPlanError("audited isosceles image metadata is required")
    by_key = {a.get("asset_key"): a for a in assets}
    if len(by_key) != len(assets) or set(by_key) - {
        "image_1",
        "image_2",
        GENERATED_KEY,
    }:
        raise ContentPlanError("unreviewed or duplicate isosceles assets are present")
    for key, asset in by_key.items():
        source = asset.get("asset_id")
        if (
            not isinstance(source, str)
            or asset.get("kind") != "ordinary_image"
            or asset.get("url") != "/assets/" + source
        ):
            raise ContentPlanError("isosceles figure metadata changed")
        if (key == "image_2" and source != HEIGHT) or (
            key == "image_1" and source not in _HASHES
        ):
            raise ContentPlanError("the isosceles figure identity is not reviewed")
    if len(set(by_key) & {"image_1", GENERATED_KEY}) != 1:
        raise ContentPlanError("the primary condition figure must have a unique key")
    for asset in assets:
        if asset["asset_id"] in _HASHES:
            source_bytes(asset["asset_id"])
    return by_key


def _asset_change(key, source, target, markup, *, existing=False):
    return {
        "transformation_target_id": "asset:" + key,
        "operation": "rewrite" if existing else "add",
        "value": {
            "asset_key": key,
            "asset_id": source,
            "url": "/assets/" + source,
            "kind": "ordinary_image",
            "alt": "",
            "parent_target_id": target,
            "position": 0,
            "html": markup,
        },
    }


def _image(key, source):
    soup = BeautifulSoup('<img alt=""/>', "html.parser")
    image = soup.img
    image["data-asset-key"] = key
    image["data-asset-id"] = source
    image["src"] = "/assets/" + source
    image["data-transformation-target-id"] = "asset:" + key
    return image


def _desired(context, generated):
    specs = diagram_specs(context)
    if not specs:
        if generated:
            raise ContentPlanError(
                "a compatible native figure needs no generated duplicate"
            )
        return "image_1", HEIGHT
    if (
        len(generated) != 1
        or generated[0].get("asset_key") != GENERATED_KEY
        or generated[0].get("sha256") != specs[0]["sha256"]
    ):
        raise ContentPlanError(
            "the uncropped figure must match the reviewed source SVG"
        )
    source = generated[0].get("source_asset_id")
    if (
        not isinstance(source, str)
        or not source
        or generated[0].get("url") != "/assets/" + source
    ):
        raise ContentPlanError("the prepared uncropped SVG identity is invalid")
    return GENERATED_KEY, source


def prepare(context, condition, generated):
    content = context["normalized_content"]
    assets = _assets(content)
    key, source = _desired(context, generated)
    old_key = next(k for k in assets if k in {"image_1", GENERATED_KEY})
    current = assets[old_key]
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1 or (
        images
        and (
            images[0].get("data-asset-key") != old_key
            or images[0].get("data-asset-id") != current["asset_id"]
            or images[0].get("data-transformation-target-id") != "asset:" + old_key
        )
    ):
        raise ContentPlanError(
            "the condition figure reference differs from its metadata"
        )
    if condition.get("asset_keys") != ([old_key] if images else []):
        raise ContentPlanError("condition figure keys differ from the actual markup")
    changes = []
    if not images or (old_key, current["asset_id"]) != (key, source):
        image = _image(key, source)
        if images:
            images[0].replace_with(image)
        elif soup.find("p"):
            soup.find("p").insert(0, image)
        else:
            soup.insert(0, image)
        changes.append(
            _asset_change(
                key,
                source,
                _targeted(condition)["transformation_target_id"],
                str(image),
                existing=key in assets,
            )
        )
        change = rewrite(
            _targeted(condition),
            "condition",
            condition.get("title", "Условие"),
            str(soup),
        )
        change["value"]["asset_keys"] = [key]
        changes.append(change)
        if old_key != key:
            changes.append(
                {"transformation_target_id": "asset:" + old_key, "operation": "remove"}
            )
    if key == GENERATED_KEY:
        markup = str(_image("image_2", HEIGHT))
        if "image_2" not in assets:
            changes.append(
                _asset_change("image_2", HEIGHT, "section:solution:1", markup)
            )
        return tuple(changes), "<p>" + markup + "</p>", ("image_2",)
    if "image_2" in assets:
        changes.append(
            {"transformation_target_id": "asset:image_2", "operation": "remove"}
        )
    return tuple(changes), "", ()
