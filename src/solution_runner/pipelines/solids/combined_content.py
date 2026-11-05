"""Remove a reviewed repeated cone-cylinder image reference without mutating input."""

from copy import deepcopy

from bs4 import BeautifulSoup

from ..quadrilaterals.quantity_content import read_content


def unique_diagram(context):
    content = context.get("normalized_content")
    if not isinstance(content, dict):
        return context
    sections = content.get("sections")
    if not isinstance(sections, list) or any(not isinstance(s, dict) for s in sections):
        return context
    roles = {s.get("key"): s for s in sections if isinstance(s, dict)}
    if not {"condition", "solution"} <= roles.keys():
        return context
    if not all(
        isinstance(roles[role].get("html"), str) for role in ("condition", "solution")
    ):
        return context
    images = [
        BeautifulSoup(roles[role]["html"], "html.parser").find_all("img")
        for role in ("condition", "solution")
    ]
    if not all(
        len(items) == 1
        and items[0].get("data-asset-id") == "fa2fd65b-5c96-41b6-9115-a456caa791e2"
        for items in images
    ):
        return context
    for role in ("condition", "solution"):
        clone = deepcopy(context)
        section = next(
            s for s in clone["normalized_content"]["sections"] if s["key"] == role
        )
        soup = BeautifulSoup(section["html"], "html.parser")
        soup.img.decompose()
        section["html"], section["asset_keys"] = str(soup), []
        read_content(clone, {"image_1"})
    return clone
