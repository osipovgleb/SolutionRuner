"""Read and validate current polygon source assets."""

from __future__ import annotations

from typing import Any

if __package__:
    from .mcp_polygon_client import McpClient
    from .mcp_polygon_config import RASTER_CONTENT_TYPES, SVG_CONTENT_TYPE
    from .mcp_polygon_inventory import _normalized_content_type
    from .mcp_polygon_models import (
        AssetCandidate,
        CandidateStale,
        PipelineError,
        PreparedAsset,
        RefreshedAsset,
    )
else:
    from mcp_polygon_client import McpClient
    from mcp_polygon_config import RASTER_CONTENT_TYPES, SVG_CONTENT_TYPE
    from mcp_polygon_inventory import _normalized_content_type
    from mcp_polygon_models import (
        AssetCandidate,
        CandidateStale,
        PipelineError,
        PreparedAsset,
        RefreshedAsset,
    )


def _current_asset_for_candidate(
    context: dict[str, Any], candidate: AssetCandidate
) -> dict[str, Any]:
    """Return the unique current normalized asset matching one candidate."""

    normalized = context.get("normalized_content")
    assets = normalized.get("assets", []) if isinstance(normalized, dict) else []
    matches = [
        asset
        for asset in assets
        if isinstance(asset, dict)
        and str(asset.get("asset_key") or "") == candidate.asset_key
        and str(asset.get("kind") or "") == "ordinary_image"
    ]
    if len(matches) != 1:
        raise CandidateStale(
            f"expected one current ordinary asset, found {len(matches)}"
        )
    return matches[0]


def refresh_candidate(client: McpClient, candidate: AssetCandidate) -> RefreshedAsset:
    """Re-read one candidate and its exact replacement decision context."""

    transformation_context = client.call(
        "get_problem_transformation_context",
        {"problem_id": candidate.problem_id},
    )
    asset = _current_asset_for_candidate(transformation_context, candidate)
    content_type = _normalized_content_type(asset.get("content_type"))
    if content_type and content_type not in RASTER_CONTENT_TYPES:
        raise CandidateStale(
            f"current content_type is {content_type or 'missing'}, not a supported raster"
        )
    target_id = str(asset.get("transformation_target_id") or "")
    if not target_id:
        raise CandidateStale("current PNG has no transformation_target_id")
    replacement_context = client.call(
        "get_problem_asset_target_context",
        {
            "problem_id": candidate.problem_id,
            "transformation_target_id": target_id,
        },
    )
    current_asset = replacement_context.get("current_asset")
    if not isinstance(current_asset, dict):
        raise CandidateStale("replacement context has no current_asset")
    if str(current_asset.get("asset_key") or "") != candidate.asset_key:
        raise CandidateStale("replacement context resolved another asset_key")
    replacement_content_type = _normalized_content_type(
        current_asset.get("content_type")
    )
    if (
        replacement_content_type
        and replacement_content_type not in RASTER_CONTENT_TYPES
    ):
        raise CandidateStale(
            "replacement context no longer points to a supported raster"
        )
    if str(replacement_context.get("transformation_target_id") or "") != target_id:
        raise CandidateStale("replacement target changed during re-read")
    return RefreshedAsset(
        transformation_target_id=target_id,
        asset=current_asset,
        replacement_context=replacement_context,
    )


def _verify_source_asset(
    client: McpClient,
    *,
    source_asset_id: str,
    prepared: PreparedAsset,
) -> dict[str, Any]:
    """Re-read and verify one uploaded reusable source asset."""

    payload = client.call("get_source_asset", {"source_asset_id": source_asset_id})
    asset = payload.get("source_asset")
    if not isinstance(asset, dict):
        raise PipelineError("uploaded source asset cannot be re-read")
    if str(asset.get("id") or asset.get("source_asset_id") or "") != source_asset_id:
        raise PipelineError("get_source_asset returned another id")
    if str(asset.get("canonical_asset_key") or "") != prepared.canonical_asset_key:
        raise PipelineError("uploaded source asset has another canonical key")
    if _normalized_content_type(asset.get("content_type")) != SVG_CONTENT_TYPE:
        raise PipelineError("uploaded source asset is not SVG")
    if str(asset.get("sha256") or "").lower() != prepared.output_sha256:
        raise PipelineError("uploaded source asset sha256 differs from local SVG")
    return asset
