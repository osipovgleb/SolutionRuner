"""Inspect sections and build safe isosceles content transformations."""

from __future__ import annotations

import re
from html import escape, unescape
from typing import Any

from bs4 import BeautifulSoup, Tag

from .planner_types import IsoscelesTrianglePlanError


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    """Return one unique normalized section by canonical key."""

    matches = [
        item
        for item in content.get("sections", [])
        if isinstance(item, dict) and item.get("key") == key
    ]
    if len(matches) > 1:
        raise IsoscelesTrianglePlanError(f"multiple {key} sections are present")
    return matches[0] if matches else None


def _plain_html(value: str) -> str:
    """Return visible normalized text for emptiness and answer checks."""

    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value))).strip()


def _target(section: dict[str, Any] | None, key: str) -> str:
    """Return the exact current section target or its canonical add target."""

    if section is not None:
        exact = str(section.get("transformation_target_id") or "")
        if exact:
            return exact
        section_id = str(section.get("section_id") or "")
        if section_id:
            return f"section:{section_id}"
    return f"section:{key}"


def _section_transformation(
    section: dict[str, Any] | None,
    key: str,
    title: str,
    html: str,
    *,
    asset_keys: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Build one exact add or rewrite operation for a normalized section."""

    return {
        "transformation_target_id": _target(section, key),
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": list(asset_keys)},
    }


def _asset_transformation(parent_condition_asset_id: str) -> dict[str, Any]:
    """Attach the parent condition image at the canonical first position."""

    return {
        "transformation_target_id": "asset:image_1",
        "operation": "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": "image_1",
            "asset_id": parent_condition_asset_id,
            "url": f"/assets/{parent_condition_asset_id}",
            "kind": "ordinary_image",
            "alt": "",
            "html": (
                f'<center><img alt="" data-asset-id="{parent_condition_asset_id}" '
                f'data-asset-key="image_1" src="/assets/{parent_condition_asset_id}"/></center>'
            ),
        },
    }


def _without_asset_markup(
    section: dict[str, Any], asset_key: str
) -> tuple[str, tuple[str, ...]]:
    """Remove one misplaced image while preserving all substantive section content."""

    soup = BeautifulSoup(str(section.get("html") or ""), "html.parser")
    for image in list(soup.find_all("img", attrs={"data-asset-key": asset_key})):
        wrapper = image.parent
        image.decompose()
        if (
            isinstance(wrapper, Tag)
            and wrapper.name in {"p", "center", "figure"}
            and not wrapper.get_text(strip=True)
            and wrapper.find(("img", "audio", "video")) is None
        ):
            wrapper.decompose()
    keys = tuple(
        str(value)
        for value in section.get("asset_keys", [])
        if str(value) and str(value) != asset_key
    )
    return str(soup), keys


def _solution_asset_transformation(
    asset: dict[str, str],
    *,
    expected_asset_key: str,
) -> dict[str, Any]:
    """Attach one parent-owned solution image to the canonical solution section."""

    asset_key = str(asset.get("asset_key") or "")
    asset_id = str(asset.get("source_asset_id") or "")
    url = str(asset.get("url") or f"/assets/{asset_id}")
    alt = str(asset.get("alt") or "")
    if asset_key != expected_asset_key or not asset_id:
        raise IsoscelesTrianglePlanError(
            f"parent must provide exactly solution asset {expected_asset_key}"
        )
    html = (
        f'<center><img alt="{escape(alt, quote=True)}" '
        f'data-asset-id="{escape(asset_id, quote=True)}" '
        f'data-asset-key="{escape(asset_key, quote=True)}" '
        f'src="{escape(url, quote=True)}"/></center>'
    )
    return {
        "transformation_target_id": f"asset:{asset_key}",
        "operation": "add",
        "value": {
            "parent_target_id": "section:solution",
            "position": 0,
            "asset_key": asset_key,
            "asset_id": asset_id,
            "url": url,
            "kind": "ordinary_image",
            "alt": alt,
            "html": html,
        },
    }


def _condition_asset_transformation(
    asset: dict[str, str],
    *,
    expected_asset_key: str,
) -> dict[str, Any]:
    """Move one parent-owned diagram to the centered condition position."""

    asset_key = str(asset.get("asset_key") or "")
    asset_id = str(asset.get("source_asset_id") or "")
    url = str(asset.get("url") or f"/assets/{asset_id}")
    alt = str(asset.get("alt") or "")
    if asset_key != expected_asset_key or not asset_id:
        raise IsoscelesTrianglePlanError(
            f"parent must provide exactly condition asset {expected_asset_key}"
        )
    html = (
        f'<center><img alt="{escape(alt, quote=True)}" '
        f'data-asset-id="{escape(asset_id, quote=True)}" '
        f'data-asset-key="{escape(asset_key, quote=True)}" '
        f'src="{escape(url, quote=True)}"/></center>'
    )
    return {
        "transformation_target_id": f"asset:{asset_key}",
        "operation": "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": asset_key,
            "asset_id": asset_id,
            "url": url,
            "kind": "ordinary_image",
            "alt": alt,
            "html": html,
        },
    }


def _condition_image_repairs(
    content: dict[str, Any],
    parent_solution_assets: tuple[dict[str, str], ...],
    *,
    group_key: str,
) -> tuple[dict[str, Any], ...]:
    """Place the prototype diagram in condition and remove its solution occurrence."""

    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    solution_has_image = solution is not None and (
        "image_1" in tuple(str(value) for value in solution.get("asset_keys", []))
        or BeautifulSoup(str(solution.get("html") or ""), "html.parser").find(
            "img", attrs={"data-asset-key": "image_1"}
        )
        is not None
    )
    if not solution_missing and not solution_has_image:
        return ()
    image_assets = [
        item for item in parent_solution_assets if item.get("asset_key") == "image_1"
    ]
    if len(image_assets) != 1:
        raise IsoscelesTrianglePlanError(
            f"group {group_key} parent must provide primary image_1"
        )
    transformations: list[dict[str, Any]] = [
        _condition_asset_transformation(image_assets[0], expected_asset_key="image_1")
    ]
    if solution is not None and solution_has_image:
        cleaned_html, remaining_keys = _without_asset_markup(solution, "image_1")
        transformations.insert(
            0,
            _section_transformation(
                solution,
                "solution",
                str(solution.get("title") or "Решение"),
                cleaned_html,
                asset_keys=remaining_keys,
            ),
        )
    return tuple(transformations)
