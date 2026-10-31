"""Prepare exact reuse of the inspected, parameter-independent pair-sum example."""

import hashlib
from copy import deepcopy
from importlib.resources import files

from bs4 import BeautifulSoup

from ..probability import solution_diagrams as diagrams
from ..triangles.isosceles.planner import _normalized_content, _section
from . import math_common
from .common import UnsupportedCondition

ASSET_ID = "f82e4ad2-182b-4554-befe-9149e1114e43"
ASSET_SHA256 = "fc5eea731d53e74519844484eee4142d3b991a6691479cb144967e1b5b73e486"
URL = "/assets/" + ASSET_ID


def read(context):
    prepared = deepcopy(context)
    content = _normalized_content(prepared)
    content["assets"] = []
    solution = _section(content, "solution")
    if solution:
        solution["asset_keys"] = []
    return math_common.read(prepared)


def validate(context, q):
    content = _normalized_content(context)
    assets = content.get("assets", [])
    if not isinstance(assets, list) or any(not isinstance(a, dict) for a in assets):
        raise UnsupportedCondition("canonical asset metadata must be a list of objects")
    solution = _section(content, "solution") or {}
    if any(
        s.get("asset_keys") for s in content["sections"] if s.get("key") != "solution"
    ):
        raise UnsupportedCondition("work figures may appear only in the solution")
    refs = BeautifulSoup(solution.get("html", ""), "html.parser").select(
        "img, [data-asset-id], [data-asset-key], [href*='/assets/']"
    )
    if q.kind != "work_pairs_boys":
        if assets or refs or solution.get("asset_keys"):
            raise UnsupportedCondition(
                "this work model requires text sections without figures"
            )
        return
    if not assets:
        if refs or solution.get("asset_keys"):
            raise UnsupportedCondition(
                "pair figure references require canonical asset metadata"
            )
        return
    if (
        len(assets) != 1
        or assets[0].get("asset_id") != ASSET_ID
        or assets[0].get("kind") != "ordinary_image"
        or assets[0].get("url") != URL
    ):
        raise UnsupportedCondition(
            "only the exact inspected pair-sum illustration is supported"
        )
    key = assets[0].get("asset_key")
    if (
        not isinstance(key, str)
        or not key
        or solution.get("asset_keys") != [key]
        or len(refs) != 1
    ):
        raise UnsupportedCondition(
            "one canonical pair-sum figure reference is required"
        )
    image = refs[0]
    if (
        image.name != "img"
        or image.get("data-asset-key") != key
        or image.get("data-asset-id") != ASSET_ID
        or image.get("src") != URL
    ):
        raise UnsupportedCondition(
            "the pair-sum figure reference must match its metadata"
        )


def prepare(context, q):
    validate(context, q)
    if q.kind != "work_pairs_boys":
        return "", (), ()
    blob = files(__package__).joinpath("assets/work_pairs.svg").read_bytes()
    if hashlib.sha256(blob).hexdigest() != ASSET_SHA256:
        raise UnsupportedCondition("the inspected pair-sum SVG bytes have changed")
    content = _normalized_content(context)
    assets = content.get("assets") or []
    if assets:
        markup, key, changes = diagrams.image(
            content,
            assets[0]["asset_key"],
            assets[0].get("alt", ""),
            source_id=ASSET_ID,
        )
    else:
        key = "image_1"
        source = {
            "asset_key": key,
            "source_asset_id": ASSET_ID,
            "url": URL,
            "sha256": ASSET_SHA256,
        }
        markup, key, changes = diagrams.image(
            content, key, "", svg=blob.decode("utf-8"), generated=(source,)
        )
    return markup, (key,), changes
