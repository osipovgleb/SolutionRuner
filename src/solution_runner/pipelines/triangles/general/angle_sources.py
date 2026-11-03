"""Validate one reviewed condition image before reading a triangle-angle question."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ..isosceles.planner import _section


def reviewed_condition(context, keys, source_bytes):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized triangle content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one reviewed triangle condition figure is required")
    asset = assets[0]
    key, identifier = asset.get("asset_key"), asset.get("asset_id")
    if (
        key not in {"image_1", *keys.values()}
        or not isinstance(identifier, str)
        or not identifier
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != "/assets/" + identifier
    ):
        raise ContentPlanError("the reviewed triangle image metadata changed")
    source = (
        identifier if key == "image_1" else next(s for s, k in keys.items() if k == key)
    )
    raw = source_bytes(source)
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete triangle condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError("the condition image differs from its metadata")
    images[0]["data-asset-key"] = "image_1"
    return asset, condition, source, raw, str(soup)
