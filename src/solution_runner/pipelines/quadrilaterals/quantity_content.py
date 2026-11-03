"""Validate complete ownership of reviewed quantity sections and image metadata."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError


def read_content(context, allowed_keys):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise ContentPlanError("schema-v3 normalized quantity content is required")
    sections, assets = content.get("sections"), content.get("assets")
    if (
        not isinstance(sections, list)
        or any(not isinstance(s, dict) for s in sections)
        or not isinstance(assets, list)
        or any(not isinstance(a, dict) for a in assets)
    ):
        raise ContentPlanError(
            "complete quantity sections and asset metadata are required"
        )
    by_key = {a.get("asset_key"): a for a in assets}
    if len(by_key) != len(assets) or set(by_key) - set(allowed_keys):
        raise ContentPlanError("unknown or duplicate quantity assets")
    for a in assets:
        identifier = a.get("asset_id")
        if (
            not isinstance(identifier, str)
            or not identifier
            or a.get("kind") != "ordinary_image"
            or a.get("url") != "/assets/" + identifier
        ):
            raise ContentPlanError("quantity asset metadata changed")
    owners = {}
    for section in sections:
        if not isinstance(section.get("html"), str):
            raise ContentPlanError("complete quantity section HTML is required")
        keys = []
        for image in BeautifulSoup(section["html"], "html.parser").find_all("img"):
            key = image.get("data-asset-key")
            if (
                key not in by_key
                or key in owners
                or section.get("key") not in {"condition", "solution"}
            ):
                raise ContentPlanError("ambiguous quantity figure ownership")
            asset = by_key[key]
            if (
                image.get("data-asset-id") != asset["asset_id"]
                or image.get("src") != asset["url"]
                or image.get("data-transformation-target-id", "asset:" + key)
                != "asset:" + key
            ):
                raise ContentPlanError("the quantity image differs from its metadata")
            owners[key] = section["key"]
            keys.append(key)
        if section.get("asset_keys", []) != keys:
            raise ContentPlanError("quantity section keys differ from image references")
    if set(owners) != set(by_key):
        raise ContentPlanError("unreferenced quantity asset metadata")
    return content, by_key, owners
