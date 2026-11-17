"""Sanitize preview HTML and materialize transformations locally."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from bs4 import BeautifulSoup

ALLOWED_ATTRIBUTES = {
    "alt",
    "class",
    "colspan",
    "data-align",
    "data-asset-id",
    "data-asset-key",
    "data-cell-tone",
    "data-formula-render-mode",
    "data-inline-latex",
    "data-solution-title",
    "data-valign",
    "height",
    "href",
    "rowspan",
    "src",
    "title",
    "width",
}


def _safe_html(html: str, assets: Mapping[str, str]) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(("script", "style", "iframe", "object", "embed")):
        tag.decompose()
    for tag in soup.find_all(True):
        for attribute in list(tag.attrs):
            if (
                attribute.lower().startswith("on")
                or attribute not in ALLOWED_ATTRIBUTES
            ):
                del tag.attrs[attribute]
        if tag.has_attr("src"):
            source = str(tag.get("src") or "")
            if not source.startswith(("https://", "http://", "/")):
                del tag.attrs["src"]
        if tag.name == "img":
            key = str(tag.get("data-asset-key") or "")
            if key in assets:
                tag["src"] = assets[key]
    body = soup.body
    return "".join(str(node) for node in (body.contents if body else soup.contents))


def _asset_keys_in_html(html: str) -> set[str]:
    return {
        str(tag.get("data-asset-key"))
        for tag in BeautifulSoup(html, "lxml").find_all(attrs={"data-asset-key": True})
    }


def _asset_fragment(html: str, asset_key: str) -> str:
    tag = BeautifulSoup(html, "lxml").find(attrs={"data-asset-key": asset_key})
    if tag is None:
        return ""
    parent = tag.parent
    if (
        parent is not None
        and parent.name in {"p", "center"}
        and not parent.get_text(strip=True)
    ):
        return str(parent)
    return str(tag)


def _apply_section(sections, target_id, operation, value):
    match = next(
        (
            section
            for section in sections
            if section.get("transformation_target_id") == target_id
        ),
        None,
    )
    if operation == "remove":
        sections[:] = [section for section in sections if section is not match]
    elif operation in {"add", "rewrite"} and isinstance(value, dict):
        previous_html = str((match or {}).get("html") or "")
        updates = {
            key: deepcopy(item)
            for key, item in value.items()
            if key in {"html", "title", "asset_keys"}
        }
        if "html" in updates and "asset_keys" in updates:
            present = _asset_keys_in_html(str(updates["html"]))
            retained = "".join(
                _asset_fragment(previous_html, str(key))
                for key in updates["asset_keys"]
                if str(key) not in present
            )
            updates["html"] = retained + str(updates["html"])
        if match is None and operation == "add":
            sections.append(
                {
                    "key": target_id.split(":", 2)[1],
                    "transformation_target_id": target_id,
                    **updates,
                }
            )
        elif match is not None:
            match.update(updates)


def _apply_asset(sections, assets, target_id, operation, value):
    key = target_id.split(":", 1)[1]
    if operation == "remove":
        assets[:] = [asset for asset in assets if asset.get("asset_key") != key]
    elif operation in {"add", "rewrite"} and isinstance(value, dict):
        match = next((asset for asset in assets if asset.get("asset_key") == key), None)
        if match is None:
            assets.append(deepcopy(value))
        else:
            match.update(deepcopy(value))
        parent_id = str(value.get("parent_target_id") or "")
        parent = next(
            (
                section
                for section in sections
                if section.get("transformation_target_id") == parent_id
            ),
            None,
        )
        fragment = str(value.get("html") or "")
        if parent is not None and fragment:
            parent_html = str(parent.get("html") or "")
            if key not in _asset_keys_in_html(parent_html):
                parent["html"] = (
                    fragment + parent_html
                    if int(value.get("position") or 0) == 0
                    else parent_html + fragment
                )
            parent_keys = parent.setdefault("asset_keys", [])
            if key not in parent_keys:
                parent_keys.append(key)


def _apply_locally(
    content: Mapping[str, Any], transformations: list[dict[str, Any]]
) -> dict[str, Any]:
    """Materialize a dry-run plan in memory without an MCP write."""

    result = deepcopy(dict(content))
    sections = result.setdefault("sections", [])
    assets = result.setdefault("assets", [])
    for transformation in transformations:
        target_id = str(transformation.get("transformation_target_id") or "")
        operation = transformation.get("operation")
        value = transformation.get("value")
        if target_id.startswith("section:"):
            _apply_section(sections, target_id, operation, value)
        elif target_id.startswith("asset:"):
            _apply_asset(sections, assets, target_id, operation, value)
    return result
