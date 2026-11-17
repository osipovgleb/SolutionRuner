"""Extract and fingerprint normalized content for frozen repair plans."""

import hashlib
import json
from typing import Any

from .errors import ContentPlanError as RightTrianglePlanError


def _resolved_group(payload: dict[str, Any]) -> str:
    """Extract one stable source-group UUID from a path-resolution response."""

    matches = payload.get("matches")
    group_id = ""
    if isinstance(matches, list) and len(matches) == 1:
        match = matches[0]
        group = match.get("group") if isinstance(match, dict) else None
        group_id = str(group.get("uuid") or "") if isinstance(group, dict) else ""
    if not group_id:
        raise RightTrianglePlanError(
            "source group path resolution must return one group UUID"
        )
    return group_id


def _condition_asset_id(context: dict[str, Any]) -> str:
    """Return the first group task's unique ordinary image_1 asset identity."""

    content = context.get("normalized_content")
    assets = content.get("assets") if isinstance(content, dict) else None
    matches = [
        item
        for item in (assets if isinstance(assets, list) else [])
        if isinstance(item, dict)
        and item.get("asset_key") == "image_1"
        and item.get("kind") == "ordinary_image"
        and item.get("asset_id")
    ]
    if len(matches) != 1:
        raise RightTrianglePlanError(
            "first group problem must have one ordinary image_1 asset"
        )
    return str(matches[0]["asset_id"])


def _solution_assets(context: dict[str, Any]) -> tuple[dict[str, str], ...]:
    """Return parent assets explicitly referenced by its solution section."""

    content = context.get("normalized_content")
    sections = content.get("sections") if isinstance(content, dict) else None
    solution_matches = [
        item
        for item in (sections if isinstance(sections, list) else [])
        if isinstance(item, dict) and item.get("key") == "solution"
    ]
    if len(solution_matches) > 1:
        raise RightTrianglePlanError("first group problem has multiple solutions")
    if not solution_matches:
        return ()
    keys = tuple(
        str(value) for value in solution_matches[0].get("asset_keys", []) if str(value)
    )
    assets = content.get("assets") if isinstance(content, dict) else None
    by_key = {
        str(item.get("asset_key")): item
        for item in (assets if isinstance(assets, list) else [])
        if isinstance(item, dict) and item.get("asset_key") and item.get("asset_id")
    }
    if any(key not in by_key for key in keys):
        raise RightTrianglePlanError("first group solution asset is unresolved")
    return tuple(
        {
            "asset_key": key,
            "source_asset_id": str(by_key[key]["asset_id"]),
            "url": str(by_key[key].get("url") or f"/assets/{by_key[key]['asset_id']}"),
            "alt": str(by_key[key].get("alt") or ""),
        }
        for key in keys
    )


def _solution_html(context: dict[str, Any]) -> str:
    content = context.get("normalized_content")
    sections = content.get("sections") if isinstance(content, dict) else None
    for item in sections if isinstance(sections, list) else []:
        if isinstance(item, dict) and item.get("key") == "solution":
            return str(item.get("html") or "")
    return ""


def _context_fingerprint(context: dict[str, Any]) -> str:
    """Fingerprint the materialized inputs used to freeze one repair record."""

    content = context.get("normalized_content")
    encoded = json.dumps(
        content,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()
