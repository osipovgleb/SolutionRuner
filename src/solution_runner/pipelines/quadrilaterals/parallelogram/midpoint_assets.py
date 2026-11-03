"""Check every image reference and its condition or solution ownership."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from .midpoint_sources import SOURCES, source_bytes

PREFIX = "midpoint_"


def seed(asset):
    key = asset["asset_key"]
    source = key.removeprefix(PREFIX) if key.startswith(PREFIX) else asset["asset_id"]
    source_bytes(source)
    return source


def read_assets(content):
    assets, sections = content.get("assets"), content.get("sections")
    if not isinstance(assets, list) or any(not isinstance(a, dict) for a in assets):
        raise ContentPlanError("complete midpoint asset metadata is required")
    by_key = {a.get("asset_key"): a for a in assets}
    if len(by_key) != len(assets) or any(not isinstance(k, str) for k in by_key):
        raise ContentPlanError("duplicate or invalid midpoint asset keys")
    for key, asset in by_key.items():
        identifier = asset.get("asset_id")
        if key not in {"image_1", "image_2"} and not key.startswith(PREFIX):
            raise ContentPlanError("unreviewed midpoint asset key")
        if (
            not isinstance(identifier, str)
            or not identifier
            or asset.get("kind") != "ordinary_image"
            or asset.get("url") != "/assets/" + identifier
        ):
            raise ContentPlanError("midpoint asset metadata changed")
        seed(asset)
    if not isinstance(sections, list) or any(not isinstance(s, dict) for s in sections):
        raise ContentPlanError("complete midpoint sections are required")
    owners = {}
    for section in sections:
        if not isinstance(section.get("html"), str):
            raise ContentPlanError("complete midpoint section HTML is required")
        images = BeautifulSoup(section["html"], "html.parser").find_all("img")
        keys = []
        for image in images:
            key = image.get("data-asset-key")
            if (
                key not in by_key
                or key in owners
                or section.get("key") not in {"condition", "solution"}
            ):
                raise ContentPlanError("ambiguous midpoint figure ownership")
            asset = by_key[key]
            if (
                image.get("data-asset-id") != asset["asset_id"]
                or image.get("src") != asset["url"]
                or image.get("data-transformation-target-id", "asset:" + key)
                != "asset:" + key
            ):
                raise ContentPlanError("the midpoint figure differs from its metadata")
            owners[key] = section["key"]
            keys.append(key)
        if section.get("asset_keys", []) != keys:
            raise ContentPlanError("midpoint section keys differ from its images")
    if set(owners) != set(by_key):
        raise ContentPlanError("unreferenced midpoint figure metadata")
    for key, owner in owners.items():
        part = SOURCES[seed(by_key[key])][2]
        if (part == "condition") != (owner == "condition"):
            raise ContentPlanError("the midpoint figure belongs to another method")
    return by_key, owners
