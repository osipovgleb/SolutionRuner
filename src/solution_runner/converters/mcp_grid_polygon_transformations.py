#!/usr/bin/env python3
"""Discover current grid-polygon PNGs and replace them through TeacherHelper MCP."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

if __package__:
    from . import (
        mcp_polygon_asset_state,
        mcp_polygon_cli,
        mcp_polygon_client,
        mcp_polygon_config,
        mcp_polygon_converter,
        mcp_polygon_events,
        mcp_polygon_groups,
        mcp_polygon_inventory,
        mcp_polygon_models,
        mcp_polygon_operations,
        mcp_polygon_processing,
        mcp_polygon_resume,
        mcp_polygon_rollback,
        mcp_polygon_run_state,
        mcp_polygon_transfer,
        mcp_polygon_util,
        mcp_polygon_validation,
        mcp_polygon_worklist,
        mcp_polygon_worklist_build,
    )
else:
    import mcp_polygon_asset_state
    import mcp_polygon_cli
    import mcp_polygon_client
    import mcp_polygon_config
    import mcp_polygon_converter
    import mcp_polygon_events
    import mcp_polygon_groups
    import mcp_polygon_inventory
    import mcp_polygon_models
    import mcp_polygon_operations
    import mcp_polygon_processing
    import mcp_polygon_resume
    import mcp_polygon_rollback
    import mcp_polygon_run_state
    import mcp_polygon_transfer
    import mcp_polygon_util
    import mcp_polygon_validation
    import mcp_polygon_worklist
    import mcp_polygon_worklist_build

DEFAULT_MCP_URL = mcp_polygon_config.DEFAULT_MCP_URL
DEFAULT_CATALOG_SNAPSHOT_ID = mcp_polygon_config.DEFAULT_CATALOG_SNAPSHOT_ID
DEFAULT_SOURCE_SITE_ID = mcp_polygon_config.DEFAULT_SOURCE_SITE_ID
DEFAULT_CATEGORY_KEY = mcp_polygon_config.DEFAULT_CATEGORY_KEY
DEFAULT_CATEGORY_TITLE = mcp_polygon_config.DEFAULT_CATEGORY_TITLE
DEFAULT_THEME_TITLES = mcp_polygon_config.DEFAULT_THEME_TITLES
EXPECTED_VERTICES_BY_THEME = mcp_polygon_config.EXPECTED_VERTICES_BY_THEME
FIXED_THEME_CONFIG = mcp_polygon_config.FIXED_THEME_CONFIG
FIXED_SOURCE_GROUPS = mcp_polygon_config.FIXED_SOURCE_GROUPS
REQUIRED_MCP_TOOLS = mcp_polygon_config.REQUIRED_MCP_TOOLS
REQUIRED_ROLLBACK_MCP_TOOLS = mcp_polygon_config.REQUIRED_ROLLBACK_MCP_TOOLS
PNG_CONTENT_TYPE = mcp_polygon_config.PNG_CONTENT_TYPE
BMP_CONTENT_TYPES = mcp_polygon_config.BMP_CONTENT_TYPES
RASTER_CONTENT_TYPES = mcp_polygon_config.RASTER_CONTENT_TYPES
SVG_CONTENT_TYPE = mcp_polygon_config.SVG_CONTENT_TYPE
MCP_PROTOCOL_VERSION = mcp_polygon_config.MCP_PROTOCOL_VERSION
CONVERTER_PROFILE = mcp_polygon_config.CONVERTER_PROFILE
ANSI_RESET = mcp_polygon_events.ANSI_RESET
ANSI_BOLD = mcp_polygon_events.ANSI_BOLD
ANSI_RED = mcp_polygon_events.ANSI_RED
ANSI_GREEN = mcp_polygon_events.ANSI_GREEN
ANSI_YELLOW = mcp_polygon_events.ANSI_YELLOW
ANSI_BLUE = mcp_polygon_events.ANSI_BLUE
ANSI_MAGENTA = mcp_polygon_events.ANSI_MAGENTA
ANSI_CYAN = mcp_polygon_events.ANSI_CYAN
ANSI_BRIGHT_GREEN = mcp_polygon_events.ANSI_BRIGHT_GREEN
TASK_STAGE_STYLES = mcp_polygon_events.TASK_STAGE_STYLES


PipelineError = mcp_polygon_models.PipelineError
McpCallError = mcp_polygon_models.McpCallError
CandidateRejected = mcp_polygon_models.CandidateRejected
CandidateStale = mcp_polygon_models.CandidateStale
ThemeScope = mcp_polygon_models.ThemeScope
GroupScope = mcp_polygon_models.GroupScope
AssetCandidate = mcp_polygon_models.AssetCandidate
GroupInventory = mcp_polygon_models.GroupInventory
RefreshedAsset = mcp_polygon_models.RefreshedAsset
PreparedAsset = mcp_polygon_models.PreparedAsset
RollbackCandidate = mcp_polygon_models.RollbackCandidate
_CandidateOutcome = mcp_polygon_models._CandidateOutcome


_DeterminismGate = mcp_polygon_converter._DeterminismGate


_ProcessingContext = mcp_polygon_processing._ProcessingContext


EventLogger = mcp_polygon_events.EventLogger
McpClient = mcp_polygon_client.McpClient
_compact_error = mcp_polygon_client._compact_error
_safe_exception = mcp_polygon_client._safe_exception
_mcp_content_text = mcp_polygon_client._mcp_content_text
_unpack_mcp_result = mcp_polygon_client._unpack_mcp_result
_chunks = mcp_polygon_util._chunks
_bounded_map_ordered = mcp_polygon_util._bounded_map_ordered
_sha256_bytes = mcp_polygon_util._sha256_bytes
_sha256_file = mcp_polygon_util._sha256_file
_atomic_write_json = mcp_polygon_util._atomic_write_json
_normalized_content_type = mcp_polygon_inventory._normalized_content_type
_validate_startup = mcp_polygon_client._validate_startup
discover_catalog_scope = mcp_polygon_inventory.discover_catalog_scope
_load_group_targets = mcp_polygon_inventory._load_group_targets
build_group_inventory = mcp_polygon_inventory.build_group_inventory
_current_asset_for_candidate = mcp_polygon_asset_state._current_asset_for_candidate
refresh_candidate = mcp_polygon_asset_state.refresh_candidate
_transfer_get = mcp_polygon_transfer._transfer_get
_transfer_put = mcp_polygon_transfer._transfer_put
_validate_png = mcp_polygon_transfer._validate_png
_load_converter = mcp_polygon_converter._load_converter
_parse_diagnostics = mcp_polygon_validation._parse_diagnostics
_polygon_area = mcp_polygon_validation._polygon_area
_validate_diagnostics = mcp_polygon_validation._validate_diagnostics
_validate_svg = mcp_polygon_validation._validate_svg
_canonical_asset_key = mcp_polygon_converter._canonical_asset_key
_polygon_alt_text = mcp_polygon_converter._polygon_alt_text


def prepare_candidate(
    client: McpClient,
    *,
    candidate: AssetCandidate,
    converter: Any,
    converter_fingerprint: str,
    template_path: Path,
    run_dir: Path,
    transfer_timeout_seconds: float,
    logger: EventLogger,
) -> PreparedAsset:
    return mcp_polygon_operations.prepare_candidate(
        client=client,
        candidate=candidate,
        converter=converter,
        converter_fingerprint=converter_fingerprint,
        template_path=template_path,
        run_dir=run_dir,
        transfer_timeout_seconds=transfer_timeout_seconds,
        logger=logger,
        services=SimpleNamespace(
            refresh_candidate=refresh_candidate,
            _transfer_get=_transfer_get,
        ),
    )


verify_first_deterministic_render = (
    mcp_polygon_converter.verify_first_deterministic_render
)


_verify_source_asset = mcp_polygon_asset_state._verify_source_asset


def apply_prepared_asset(
    client: McpClient,
    *,
    source_site_id: str,
    prepared: PreparedAsset,
    transfer_timeout_seconds: float,
    logger: EventLogger,
) -> tuple[str, dict[str, Any]]:
    return mcp_polygon_operations.apply_prepared_asset(
        client=client,
        source_site_id=source_site_id,
        prepared=prepared,
        transfer_timeout_seconds=transfer_timeout_seconds,
        logger=logger,
        services=SimpleNamespace(
            _transfer_put=_transfer_put,
            _verify_source_asset=_verify_source_asset,
        ),
    )


_process_candidate = mcp_polygon_processing._process_candidate
_process_problem_unit = mcp_polygon_processing._process_problem_unit
_problem_units = mcp_polygon_processing._problem_units
_problem_batches = mcp_polygon_processing._problem_batches
_assert_locked_inputs = mcp_polygon_processing._assert_locked_inputs
_new_totals = mcp_polygon_util._new_totals
build_run_worklist = mcp_polygon_worklist_build.build_run_worklist
_read_json_object = mcp_polygon_worklist._read_json_object
_read_run_events = mcp_polygon_worklist._read_run_events
_validated_source_run_dir = mcp_polygon_worklist._validated_source_run_dir
_load_validated_worklist = mcp_polygon_worklist._load_validated_worklist
_event_candidate_key = mcp_polygon_worklist._event_candidate_key
_resume_inventory_from_run = mcp_polygon_resume._resume_inventory_from_run
_rollback_inventory_from_run = mcp_polygon_resume._rollback_inventory_from_run
_rollback_batches = mcp_polygon_rollback._rollback_batches
_rollback_error_is_stale = mcp_polygon_rollback._rollback_error_is_stale
_execute_rollback = mcp_polygon_rollback._execute_rollback
_validate_write_batch_policy = mcp_polygon_processing._validate_write_batch_policy


def _process_discovered_run(run):
    args = run.args
    client = run.client
    logger = run.logger
    run_dir = run.run_dir
    source_site_id = run.source_site_id
    scope = run.scope
    converter_path = run.converter_path
    converter_fingerprint = run.converter_fingerprint
    template_path = run.template_path
    template_fingerprint = run.template_fingerprint
    converter = run.converter
    user_id = run.user_id
    apply = run.apply
    inventory_by_group, totals = mcp_polygon_run_state.prepare_inventory(
        args,
        client,
        mcp_polygon_run_state.InventoryContext(
            run_dir,
            source_site_id,
            scope,
            converter_fingerprint,
            template_fingerprint,
            logger,
        ),
        (_resume_inventory_from_run, build_run_worklist),
    )
    determinism_gate = _DeterminismGate(
        converter=converter,
        template_path=template_path,
        run_dir=run_dir,
    )

    processing_scope = [] if args.mode == "inventory" else scope
    group_context = SimpleNamespace(
        logger=logger,
        converter_path=converter_path,
        converter_fingerprint=converter_fingerprint,
        template_path=template_path,
        template_fingerprint=template_fingerprint,
        inventory_by_group=inventory_by_group,
        args=args,
        client=client,
        source_site_id=source_site_id,
        converter=converter,
        run_dir=run_dir,
        apply=apply,
        determinism_gate=determinism_gate,
        prepare_candidate=prepare_candidate,
        apply_prepared_asset=apply_prepared_asset,
        verify_first_deterministic_render=verify_first_deterministic_render,
        processing_context_type=_ProcessingContext,
        totals=totals,
    )
    global_tasks_seen, batches_seen, determinism_verified, stop_requested = (
        mcp_polygon_groups.process_groups(group_context, processing_scope)
    )

    return mcp_polygon_run_state.finish_run(
        args,
        logger,
        (
            run_dir,
            user_id,
            source_site_id,
            converter_fingerprint,
            template_fingerprint,
        ),
        (
            global_tasks_seen,
            batches_seen,
            determinism_verified,
            stop_requested,
            totals,
        ),
        _atomic_write_json,
    )


def run_pipeline(args: argparse.Namespace) -> int:
    """Run discovery, deterministic conversion, optional upload, and readback."""

    apply = args.mode == "apply"
    rollback = args.mode == "rollback"
    writes = apply or rollback
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    logger = EventLogger(run_dir / "events.jsonl", color="always")
    client: McpClient | None = None
    summary: dict[str, Any] = {}
    try:
        (
            api_key,
            converter_path,
            template_path,
            converter_fingerprint,
            template_fingerprint,
            converter,
        ) = mcp_polygon_converter.prepare_run_inputs(args, writes=writes)

        mcp_polygon_run_state.emit_start(
            args, logger, run_dir, (converter_fingerprint, template_fingerprint)
        )
        client = McpClient(
            url=args.mcp_url,
            api_key=api_key,
            timeout_seconds=args.mcp_timeout_seconds,
            logger=logger,
        )
        user_id = _validate_startup(client, mode=args.mode, logger=logger)
        source_site_id, scope = discover_catalog_scope(
            client,
            catalog_snapshot_id=args.catalog_snapshot_id,
            category_key=args.category_key,
            category_title=args.category_title,
            theme_titles=args.theme_titles,
            group_keys=args.group_keys,
            logger=logger,
        )
        if rollback:
            return mcp_polygon_rollback.finish_rollback_run(
                client,
                args=args,
                run_dir=run_dir,
                logger=logger,
                user_id=user_id,
                source_site_id=source_site_id,
                scope=scope,
            )

        return _process_discovered_run(
            SimpleNamespace(
                args=args,
                client=client,
                logger=logger,
                run_dir=run_dir,
                source_site_id=source_site_id,
                scope=scope,
                converter_path=converter_path,
                converter_fingerprint=converter_fingerprint,
                template_path=template_path,
                template_fingerprint=template_fingerprint,
                converter=converter,
                user_id=user_id,
                apply=apply,
            )
        )
    except BaseException as exc:
        summary = {
            "at": datetime.now(UTC).isoformat(),
            "status": "failed",
            "mode": getattr(args, "mode", None),
            "run_dir": str(run_dir),
            "reason": _safe_exception(exc),
            "error_type": type(exc).__name__,
        }
        _atomic_write_json(run_dir / "summary.json", summary)
        logger.emit(
            "run_failed",
            level="error",
            status="failed",
            reason=summary["reason"],
            error_type=summary["error_type"],
        )
        return 1
    finally:
        if client is not None:
            client.close()
        logger.close()


build_parser = mcp_polygon_cli.build_parser
_validate_cli_args = mcp_polygon_cli._validate_cli_args


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and return the autonomous pipeline exit code."""

    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_cli_args(args, parser)
    return run_pipeline(args)


if __name__ == "__main__":
    sys.exit(main())
