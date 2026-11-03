"""Validate every repeated solution reference before making a unique view."""

from collections import Counter
from copy import deepcopy

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import _section
from .circumcircle_isosceles_model import DETAIL, DETAIL_KEY


def validation_context(context, reader):
    content = context.get("normalized_content")
    if not isinstance(content, dict) or not isinstance(content.get("sections"), list):
        return context
    solution = _section(content, "solution")
    if solution is None or not isinstance(solution.get("html"), str):
        return context
    soup = BeautifulSoup(solution["html"], "html.parser")
    images = soup.find_all("img")
    counts = Counter(image.get("data-asset-key") for image in images)
    repeated = {key for key, count in counts.items() if count > 1}
    if not repeated or repeated - {"image_2", DETAIL_KEY}:
        return context
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError(
            "the repeated isosceles picture requires a complete condition"
        )
    condition_images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    source = (
        condition_images[0].get("data-asset-id") if len(condition_images) == 1 else None
    )
    if condition_images and (not isinstance(source, str) or not source):
        raise ContentPlanError(
            "the repeated isosceles picture requires a condition image identifier"
        )
    if reader(condition["html"], source).mode != "isosceles_radius":
        return context
    assets = content.get("assets")
    if not isinstance(assets, list) or any(not isinstance(a, dict) for a in assets):
        raise ContentPlanError(
            "the repeated solution picture requires complete metadata"
        )
    by_key = {a.get("asset_key"): a for a in assets}
    if len(by_key) != len(assets):
        raise ContentPlanError("duplicate isosceles asset metadata")
    keys = list(dict.fromkeys(image.get("data-asset-key") for image in images))
    if solution.get("asset_keys") != keys:
        raise ContentPlanError(
            "the repeated solution keys must be the ordered unique references"
        )
    seen = set()
    for image in images:
        key = image.get("data-asset-key")
        asset = by_key.get(key, {})
        identifier = asset.get("asset_id")
        if (
            key not in {"image_2", DETAIL_KEY}
            or not isinstance(identifier, str)
            or not identifier
            or (key == "image_2" and identifier != DETAIL)
            or asset.get("kind") != "ordinary_image"
            or asset.get("url") != "/assets/" + identifier
            or image.get("data-asset-id") != identifier
            or image.get("src") != asset["url"]
            or image.get("data-transformation-target-id") != "asset:" + key
            or set(image.attrs)
            - {
                "alt",
                "src",
                "data-asset-key",
                "data-asset-id",
                "data-transformation-target-id",
            }
        ):
            raise ContentPlanError(
                "every repeated isosceles solution reference must match its reviewed role"
            )
        if key in seen:
            image.decompose()
        seen.add(key)
    clean = deepcopy(context)
    _section(clean["normalized_content"], "solution")["html"] = str(soup)
    return clean
