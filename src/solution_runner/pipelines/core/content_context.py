"""Extract and fingerprint normalized content for frozen repair plans."""

import hashlib
import json
import re
from copy import deepcopy
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


def _asset_key(source_asset_id: str) -> str:
    """Mirror TeacherHelper's stable key for a shared SourceAsset attachment."""
    return "shared_" + source_asset_id.replace("-", "")[:16]


def _has_solution_section(context: dict[str, Any]) -> bool:
    """Return whether the target can accept a solution-scoped shared asset."""
    content = context.get("normalized_content")
    sections = content.get("sections") if isinstance(content, dict) else None
    return any(
        isinstance(section, dict) and section.get("key") == "solution"
        for section in sections or []
    )


def _with_solution_placeholder(context: dict[str, Any]) -> dict[str, Any]:
    """Provide the deterministic section shape used before attaching an SVG."""
    if _has_solution_section(context):
        return context
    planned = deepcopy(context)
    content = planned.get("normalized_content")
    if not isinstance(content, dict):
        raise RightTrianglePlanError(
            "normalized content is required for solution setup"
        )
    sections = content.setdefault("sections", [])
    if not isinstance(sections, list):
        raise RightTrianglePlanError("normalized content sections are invalid")
    sections.append(
        {
            "key": "solution",
            "title": "Решение",
            "html": "<p></p>",
            "asset_keys": [],
            "transformation_target_id": "section:solution:1",
        }
    )
    return planned


def _preserving_solution_transformations(
    context: dict[str, Any],
    transformations: tuple[dict[str, Any], ...],
) -> tuple[dict[str, Any], ...]:
    """Keep an editorial solution and only retain condition/answer repairs."""

    content = context.get("normalized_content")
    sections = content.get("sections") if isinstance(content, dict) else None
    solution = next(
        (
            item
            for item in sections or []
            if isinstance(item, dict) and item.get("key") == "solution"
        ),
        None,
    )
    if not solution or not str(solution.get("html") or "").strip():
        return transformations
    solution_asset_keys = {str(key) for key in solution.get("asset_keys") or []}
    kept: list[dict[str, Any]] = []
    for transformation in transformations:
        target = str(transformation.get("transformation_target_id") or "")
        value = transformation.get("value")
        parent_target = (
            str(value.get("parent_target_id") or "") if isinstance(value, dict) else ""
        )
        asset_key = target.removeprefix("asset:")
        if target.startswith("section:solution") or parent_target.startswith(
            "section:solution"
        ):
            continue
        if target.startswith("asset:") and asset_key in solution_asset_keys:
            continue
        kept.append(transformation)
    return tuple(kept)


def _children(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract the current group problem rows from either MCP list envelope."""

    candidates = payload.get("children")
    if not isinstance(candidates, list):
        candidates = payload.get("items")
    if not isinstance(candidates, list):
        raise RightTrianglePlanError("source group omitted children")
    return [item for item in candidates if isinstance(item, dict)]


def _problem_identity(item: dict[str, Any]) -> tuple[str, str]:
    """Return canonical and source ids for one source-group child row."""

    problem_id = str(item.get("problem_id") or item.get("id") or item.get("uuid") or "")
    source_problem_id = str(item.get("source_problem_id") or "")
    if not source_problem_id:
        match = re.fullmatch(r"\s*Задача\s+(.+?)\s*", str(item.get("name") or ""))
        source_problem_id = match.group(1) if match is not None else ""
    if not problem_id or not source_problem_id:
        raise RightTrianglePlanError("source group child omitted problem identity")
    return problem_id, source_problem_id
