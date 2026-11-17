"""Inspect, preview and attach assets required by a content rule."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

from .content_context import (
    _asset_key,
    _has_solution_section,
    _with_solution_placeholder,
)
from .content_gateway import RightTriangleGateway
from .errors import ContentPlanError as RightTrianglePlanError
from .models import ProblemTarget


def _current_condition_asset_content_type(
    gateway: RightTriangleGateway,
    context: dict[str, Any],
    content_rule_key: str | None,
    *,
    registered_handler: Callable[..., Any],
) -> str | None:
    """Read the current image MIME only for rules that replace raster assets."""

    if not registered_handler(content_rule_key).inspect_current_asset_type:
        return None
    content = context.get("normalized_content")
    assets = content.get("assets") if isinstance(content, dict) else None
    if not isinstance(assets, list):
        return None
    matches = [
        asset
        for asset in assets
        if isinstance(asset, dict) and asset.get("asset_key") == "image_1"
    ]
    if len(matches) != 1:
        return None
    asset = matches[0]
    asset_id = str(asset.get("asset_id") or "")
    if not asset_id:
        return None
    metadata = gateway.get_asset_metadata(asset_id)
    if str(metadata.get("asset_id") or "") != asset_id:
        raise RightTrianglePlanError("condition asset metadata identity drifted")
    content_type = str(metadata.get("content_type") or "").split(";", 1)[0].lower()
    if not content_type:
        raise RightTrianglePlanError("condition asset metadata omitted content type")
    return content_type


def _condition_asset_bytes(
    gateway: RightTriangleGateway,
    problem_id: str,
    source_problem_id: str,
    content_rule_key: str | None,
    *,
    registered_handler: Callable[..., Any],
) -> bytes | None:
    """Download a current condition image only for an explicitly declared rule."""

    if not registered_handler(content_rule_key).requires_condition_asset_download:
        return None
    asset = gateway.download_condition_asset(
        ProblemTarget(
            problem_id,
            source_problem_id,
            "",
            "",
            0,
        )
    )
    if (
        str(asset.content_type).split(";", 1)[0].lower() != "image/svg+xml"
        and not registered_handler(content_rule_key).allow_non_svg_condition_asset
    ):
        raise RightTrianglePlanError("condition asset must be SVG")
    return bytes(asset.data)


def _with_required_assets(
    context: dict[str, Any],
    content_rule_key: str | None,
    *,
    registered_handler: Callable[..., Any],
) -> dict[str, Any]:
    """Materialize missing assets locally so a safe preview can plan exactly."""
    requirements = registered_handler(content_rule_key).asset_requirements(context)
    if not requirements:
        return context
    planned = deepcopy(_with_solution_placeholder(context))
    content = planned.get("normalized_content")
    if not isinstance(content, dict):
        raise RightTrianglePlanError(
            "normalized content is required for asset selection"
        )
    assets = content.setdefault("assets", [])
    if not isinstance(assets, list):
        raise RightTrianglePlanError("normalized content assets are invalid")
    attached_ids = {
        str(item.get("asset_id")) for item in assets if isinstance(item, dict)
    }
    for requirement in requirements:
        source_asset_id = requirement["source_asset_id"]
        if source_asset_id not in attached_ids:
            assets.append(
                {"asset_key": _asset_key(source_asset_id), "asset_id": source_asset_id}
            )
    return planned


def _ensure_required_assets(
    gateway: RightTriangleGateway,
    problem_id: str,
    context: dict[str, Any],
    content_rule_key: str | None,
    *,
    registered_handler: Callable[..., Any],
) -> dict[str, Any]:
    """Attach the rule-selected assets once, then return authoritative readback."""
    requirements = registered_handler(content_rule_key).asset_requirements(context)
    if not requirements:
        return context
    if not _has_solution_section(context):
        gateway.apply_problem_transformations(
            problem_id,
            [
                {
                    "transformation_target_id": "section:solution:1",
                    "operation": "add",
                    "value": {"title": "Решение", "html": "<p></p>", "asset_keys": []},
                }
            ],
        )
        context = gateway.get_problem_context(problem_id)
        if not _has_solution_section(context):
            raise RightTrianglePlanError("solution section was not visible after setup")
    content = context.get("normalized_content")
    assets = content.get("assets") if isinstance(content, dict) else None
    attached_ids = {
        str(item.get("asset_id")) for item in assets or [] if isinstance(item, dict)
    }
    missing = [
        item for item in requirements if item["source_asset_id"] not in attached_ids
    ]
    for requirement in missing:
        gateway.attach_source_asset_to_problems(
            source_asset_id=requirement["source_asset_id"],
            section_id=requirement["section_id"],
            alt_text=requirement["alt_text"],
            problem_ids=[problem_id],
        )
    if not missing:
        return context
    refreshed = gateway.get_problem_context(problem_id)
    refreshed_assets = (refreshed.get("normalized_content") or {}).get("assets") or []
    refreshed_ids = {
        str(item.get("asset_id")) for item in refreshed_assets if isinstance(item, dict)
    }
    absent = [
        item["source_asset_id"]
        for item in requirements
        if item["source_asset_id"] not in refreshed_ids
    ]
    if absent:
        raise RightTrianglePlanError(
            "shared asset attachment was not visible after readback"
        )
    return refreshed
