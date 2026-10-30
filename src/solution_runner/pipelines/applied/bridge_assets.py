"""Read the exact bridge schematic and reuse the parent's terminology figure."""

from copy import deepcopy

from bs4 import BeautifulSoup

from ..probability import solution_diagrams as diagrams
from ..probability.common import UnsupportedCondition
from ..triangles.isosceles.planner import _normalized_content, _section
from . import common

SCHEME = "9e8f629a-111d-48c4-bd34-b761ed11a5d8"
TYPES = "ba01a676-fef4-4bb1-9c83-8782230bfcba"
HASHES = {
    SCHEME: "a50b8738467142c3cb990a423b63c37129931b4b56757f6fd364d104a869af9e",
    TYPES: "bd59c15be69a383dc87a4694e05df9935e7bb7c1d67c4170aa19fb43ac61825b",
}
ALT = "Два типа вантовых мостов: веерный слева, арфовый справа; отдельная иллюстрация к примечанию о терминологии"


def read(context):
    content = _normalized_content(context)
    if not content.get("assets"):
        return common.read(context)
    roles = {SCHEME: "condition", TYPES: "solution"}
    assets = content["assets"]
    ids = [asset.get("asset_id") for asset in assets]
    if SCHEME not in ids or len(set(ids)) != len(ids) or set(ids) - roles.keys():
        raise UnsupportedCondition(
            "the exact bridge schematic and optional terminology figure are required"
        )
    keys = {}
    for asset in assets:
        asset_id, key = asset["asset_id"], asset.get("asset_key")
        if not isinstance(key, str) or not key or key in keys:
            raise UnsupportedCondition("bridge assets need distinct exact keys")
        if (
            asset.get("url") not in [None, "/assets/" + asset_id]
            or asset.get("sha256", HASHES[asset_id]) != HASHES[asset_id]
        ):
            raise UnsupportedCondition(
                "a bridge asset URL or supplied checksum changed"
            )
        keys[key] = asset_id
    clean = deepcopy(context)
    prepared = _normalized_content(clean)
    seen = []
    for section in prepared["sections"]:
        section_keys = section.get("asset_keys", [])
        if len(set(section_keys)) != len(section_keys) or any(
            key not in keys or roles[keys[key]] != section["key"]
            for key in section_keys
        ):
            raise UnsupportedCondition(
                "bridge figures must stay in their reviewed sections"
            )
        soup = BeautifulSoup(section.get("html", ""), "html.parser")
        for img in soup.find_all("img"):
            key, asset_id = img.get("data-asset-key"), img.get("data-asset-id")
            if (
                key not in keys
                or keys[key] != asset_id
                or roles[asset_id] != section["key"]
                or key not in section_keys
                or img.get("src") not in [None, "/assets/" + asset_id]
            ):
                raise UnsupportedCondition(
                    "visible bridge images must match their exact attachments"
                )
            seen.append(asset_id)
            img.decompose()
        section["html"] = str(soup)
        section["asset_keys"] = []
    if seen.count(SCHEME) != 1 or seen.count(TYPES) > 1:
        raise UnsupportedCondition("one visible bridge schematic is required")
    prepared["assets"] = []
    _, ans, _, text = common.read(clean)
    return _section(content, "condition"), ans, _section(content, "solution"), text


def image(context):
    return diagrams.image(
        _normalized_content(context), "bridge_types", ALT, source_id=TYPES
    )


def required_asset():
    return ({"source_asset_id": TYPES, "section_id": "solution:1", "alt_text": ALT},)
