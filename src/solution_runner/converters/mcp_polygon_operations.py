"""Prepare and apply validated polygon assets through MCP."""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx

if __package__:
    from .mcp_polygon_client import McpClient, _safe_exception
    from .mcp_polygon_config import (
        BMP_CONTENT_TYPES,
        DEFAULT_MCP_URL,
        RASTER_CONTENT_TYPES,
        SVG_CONTENT_TYPE,
    )
    from .mcp_polygon_converter import _canonical_asset_key, _polygon_alt_text
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_inventory import _normalized_content_type
    from .mcp_polygon_models import (
        AssetCandidate,
        CandidateRejected,
        CandidateStale,
        PipelineError,
        PreparedAsset,
    )
    from .mcp_polygon_transfer import _validate_png
    from .mcp_polygon_util import _sha256_bytes
    from .mcp_polygon_validation import (
        _parse_diagnostics,
        _validate_diagnostics,
        _validate_svg,
    )
else:
    from mcp_polygon_client import McpClient, _safe_exception
    from mcp_polygon_config import (
        BMP_CONTENT_TYPES,
        DEFAULT_MCP_URL,
        RASTER_CONTENT_TYPES,
        SVG_CONTENT_TYPE,
    )
    from mcp_polygon_converter import _canonical_asset_key, _polygon_alt_text
    from mcp_polygon_events import EventLogger
    from mcp_polygon_inventory import _normalized_content_type
    from mcp_polygon_models import (
        AssetCandidate,
        CandidateRejected,
        CandidateStale,
        PipelineError,
        PreparedAsset,
    )
    from mcp_polygon_transfer import _validate_png
    from mcp_polygon_util import _sha256_bytes
    from mcp_polygon_validation import (
        _parse_diagnostics,
        _validate_diagnostics,
        _validate_svg,
    )


def _download_current(client, candidate, timeout_seconds, services):
    """Read and validate the current raster against its source metadata."""
    refreshed = services.refresh_candidate(client, candidate)
    current_asset_id = str(
        refreshed.replacement_context.get("current_asset_id")
        or refreshed.asset.get("asset_id")
        or ""
    )
    if not current_asset_id:
        raise CandidateStale("current raster has no asset_id")
    metadata = client.call("get_asset", {"asset_id": current_asset_id})
    file_contract = client.call("get_asset_file", {"asset_id": current_asset_id})
    contract = {
        **metadata,
        "method": "GET",
        "download_url": urljoin(
            str(getattr(client, "url", DEFAULT_MCP_URL)),
            str(file_contract.get("url") or ""),
        ),
        "headers": {},
    }
    content_type = _normalized_content_type(contract.get("content_type"))
    file_content_type = _normalized_content_type(file_contract.get("content_type"))
    if content_type not in RASTER_CONTENT_TYPES or file_content_type != content_type:
        raise CandidateStale(
            "download capability no longer describes the same supported raster"
        )
    try:
        data = services._transfer_get(contract, timeout_seconds=timeout_seconds)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in {404, 410}:
            raise CandidateStale(
                f"source raster is unavailable (HTTP {exc.response.status_code})"
            ) from exc
        raise
    input_sha256, dimensions = _validate_png(data, contract)
    current_sha = str(metadata.get("sha256") or "").lower()
    if current_sha and current_sha != input_sha256:
        raise CandidateStale("replacement context sha256 differs from downloaded PNG")
    return refreshed, data, input_sha256, dimensions, content_type


def _write_raster_artifact(run_dir, candidate, content_type, input_sha256, data):
    """Store the verified raster under its deterministic artifact path."""
    artifact_dir = (
        run_dir
        / "artifacts"
        / f"{candidate.theme_order_index:02d}-{candidate.snapshot_theme_id[:8]}"
        / f"{candidate.group_order_index:04d}-{candidate.source_group_id[:8]}"
        / f"{candidate.problem_order_index:05d}-{candidate.problem_id[:8]}"
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    safe_asset_key = "".join(
        character if character.isalnum() or character in {"-", "_"} else "_"
        for character in candidate.asset_key
    )
    input_suffix = ".bmp" if content_type in BMP_CONTENT_TYPES else ".png"
    input_path = artifact_dir / (
        f"{candidate.source_problem_id}-{safe_asset_key}-{input_sha256[:12]}{input_suffix}"
    )
    input_path.write_bytes(data)

    return artifact_dir, input_path


@dataclass(frozen=True)
class CandidatePreparation:
    converter: Any
    converter_fingerprint: str
    template_path: Path
    run_dir: Path
    transfer_timeout_seconds: float


def prepare_candidate(
    client: McpClient,
    candidate: AssetCandidate,
    preparation: CandidatePreparation,
    logger: EventLogger,
    services: Any,
) -> PreparedAsset:
    """Download, convert, and validate one current raster without MCP writes."""
    converter = preparation.converter
    converter_fingerprint = preparation.converter_fingerprint
    template_path = preparation.template_path
    run_dir = preparation.run_dir
    transfer_timeout_seconds = preparation.transfer_timeout_seconds

    refreshed, data, input_sha256, dimensions, content_type = _download_current(
        client, candidate, transfer_timeout_seconds, services
    )
    logger.emit(
        "source_downloaded",
        theme=candidate.theme_title,
        group_key=candidate.group_key,
        source_problem_id=candidate.source_problem_id,
        problem_id=candidate.problem_id,
        asset_key=candidate.asset_key,
        input_sha256=input_sha256,
        size_bytes=len(data),
    )

    artifact_dir, input_path = _write_raster_artifact(
        run_dir, candidate, content_type, input_sha256, data
    )

    converter_stdout = io.StringIO()
    try:
        svg_path = Path(
            converter.run(
                str(input_path),
                artifact_dir,
                2,
                0.97,
                20,
                1,
                1.5,
                True,
                None,
                template_path,
                False,
                expected_vertices=candidate.expected_vertices,
                output_stream=converter_stdout,
            )
        )
    except Exception as exc:  # converter failures reject only this input.
        raise CandidateRejected(f"converter failed: {_safe_exception(exc)}") from exc
    diagnostic_path = svg_path.with_suffix(".txt")
    diagnostics = _parse_diagnostics(diagnostic_path)
    validation = _validate_diagnostics(
        diagnostics,
        theme_title=candidate.theme_title,
        expected_vertices=candidate.expected_vertices,
    )
    svg_bytes = svg_path.read_bytes()
    _validate_svg(svg_bytes, expected_vertices=candidate.expected_vertices)
    output_sha256 = _sha256_bytes(svg_bytes)
    validation = {
        **validation,
        "input_dimensions": list(dimensions),
        "converter_stdout": converter_stdout.getvalue().strip().splitlines()[-4:],
    }
    alt_text = _polygon_alt_text(validation)
    return PreparedAsset(
        candidate=candidate,
        transformation_target_id=refreshed.transformation_target_id,
        input_sha256=input_sha256,
        input_size_bytes=len(data),
        output_sha256=output_sha256,
        output_size_bytes=len(svg_bytes),
        canonical_asset_key=_canonical_asset_key(output_sha256, converter_fingerprint),
        alt_text=alt_text,
        input_path=input_path,
        svg_path=svg_path,
        diagnostic_path=diagnostic_path,
        validation=validation,
    )


def _upload_verified_svg(
    client, source_site_id, prepared, transfer_timeout_seconds, logger, services
):
    """Upload the reviewed SVG and verify the reusable source asset."""
    svg_bytes = prepared.svg_path.read_bytes()
    if _sha256_bytes(svg_bytes) != prepared.output_sha256:
        raise PipelineError("local SVG changed after validation")
    upload_contract = client.call(
        "prepare_source_asset_upload",
        {
            "source_site_id": source_site_id,
            "canonical_asset_key": prepared.canonical_asset_key,
            "byte_size": len(svg_bytes),
            "sha256": prepared.output_sha256,
            "content_type": SVG_CONTENT_TYPE,
        },
    )
    logger.emit(
        "upload_link_created",
        theme=prepared.candidate.theme_title,
        group_key=prepared.candidate.group_key,
        source_problem_id=prepared.candidate.source_problem_id,
        problem_id=prepared.candidate.problem_id,
        asset_key=prepared.candidate.asset_key,
        canonical_asset_key=prepared.canonical_asset_key,
    )
    upload = services._transfer_put(
        upload_contract,
        svg_bytes,
        timeout_seconds=transfer_timeout_seconds,
    )
    source_asset_id = str(upload.get("source_asset_id") or "")
    if not source_asset_id:
        raise PipelineError("source asset upload returned no source_asset_id")
    if str(upload.get("sha256") or "").lower() != prepared.output_sha256:
        raise PipelineError("source asset upload response has another sha256")
    services._verify_source_asset(
        client,
        source_asset_id=source_asset_id,
        prepared=prepared,
    )
    logger.emit(
        "svg_uploaded",
        theme=prepared.candidate.theme_title,
        group_key=prepared.candidate.group_key,
        source_problem_id=prepared.candidate.source_problem_id,
        problem_id=prepared.candidate.problem_id,
        asset_key=prepared.candidate.asset_key,
        source_asset_id=source_asset_id,
        output_sha256=prepared.output_sha256,
    )

    return source_asset_id


def apply_prepared_asset(
    client: McpClient,
    *,
    source_site_id: str,
    prepared: PreparedAsset,
    transfer_timeout_seconds: float,
    logger: EventLogger,
    services: Any,
) -> tuple[str, dict[str, Any]]:
    """Upload a worklist-bound SVG, replace its exact target, and verify readback."""

    source_asset_id = _upload_verified_svg(
        client, source_site_id, prepared, transfer_timeout_seconds, logger, services
    )

    replacement_result = client.call(
        "replace_problem_asset",
        {
            "problem_id": prepared.candidate.problem_id,
            "transformation_target_id": prepared.transformation_target_id,
            "replacement_asset_id": source_asset_id,
            "scope": "target",
            "alt_text": prepared.alt_text,
        },
        attempts=2,
    )
    readback = client.call(
        "get_problem_asset_target_context",
        {
            "problem_id": prepared.candidate.problem_id,
            "transformation_target_id": prepared.transformation_target_id,
        },
    )
    asset = readback.get("current_asset")
    if not isinstance(asset, dict):
        raise PipelineError("replacement readback has no current_asset")
    readback_asset_id = str(
        readback.get("current_asset_id") or asset.get("asset_id") or ""
    )
    if readback_asset_id != source_asset_id:
        raise PipelineError("replacement readback points to another asset_id")
    readback_metadata = client.call("get_asset", {"asset_id": readback_asset_id})
    if (
        _normalized_content_type(readback_metadata.get("content_type"))
        != SVG_CONTENT_TYPE
    ):
        raise PipelineError("replacement readback is not SVG")
    if str(readback_metadata.get("sha256") or "").lower() != prepared.output_sha256:
        raise PipelineError("replacement readback sha256 differs from uploaded SVG")
    if str(asset.get("alt") or "") != prepared.alt_text:
        raise PipelineError("replacement readback alt differs from polygon vertices")
    cleanup = {
        "cleanup_candidate_asset_id": replacement_result.get(
            "cleanup_candidate_asset_id"
        )
    }
    return source_asset_id, cleanup if isinstance(cleanup, dict) else {}
