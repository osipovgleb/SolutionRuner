"""Accept only the audited service icons; never drop mathematical source assets."""

from copy import deepcopy

from bs4 import BeautifulSoup

from ..word_problems.common import UnsupportedCondition, section
from .exam_logarithmic_input import read as read_text

SERVICE_ICONS = {
    "image_1": "88cc43ec-bba0-4842-b479-c55a598eb26b",
    "image_2": "bb2b8fbb-239c-4263-a62c-ad9027082a6b",
}


def read(context):
    content = context.get("normalized_content") or {}
    if not content.get("assets"):
        return read_text(context)
    assets = content["assets"]
    solution = section(content, "solution")
    if (
        len(assets) != 2
        or {a.get("asset_key") for a in assets} != set(SERVICE_ICONS)
        or solution is None
        or set(solution.get("asset_keys", ())) - set(SERVICE_ICONS)
    ):
        raise UnsupportedCondition(
            "only the two audited source service icons may be omitted"
        )
    for a in assets:
        key = a.get("asset_key")
        identifier = SERVICE_ICONS.get(key)
        if (
            identifier is None
            or a.get("asset_id") != identifier
            or a.get("url") != "/assets/" + identifier
            or a.get("kind") != "ordinary_image"
        ):
            raise UnsupportedCondition("an unknown asset must not be discarded")
    soup = BeautifulSoup(solution["html"], "html.parser")
    images = soup.find_all("img")
    if images and (
        len(images) != 2
        or {i.get("data-asset-key") for i in images} != set(SERVICE_ICONS)
    ):
        raise UnsupportedCondition(
            "the original reference icons must both be identifiable"
        )
    for image in images:
        identifier = SERVICE_ICONS[image["data-asset-key"]]
        if (
            image.get("data-asset-id") != identifier
            or image.get("src") != "/assets/" + identifier
        ):
            raise UnsupportedCondition("the source reference icon identity changed")
    prepared = deepcopy(context)
    copy = prepared["normalized_content"]
    copy["assets"] = []
    section(copy, "solution")["asset_keys"] = []
    _parts, formula, interval, bounds = read_text(prepared)
    return (
        tuple(section(content, key) for key in ("condition", "answer", "solution")),
        formula,
        interval,
        bounds,
    )
