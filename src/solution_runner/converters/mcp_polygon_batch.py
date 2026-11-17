"""Prepare assets within one sequential polygon conversion batch."""

from __future__ import annotations

import httpx

if __package__:
    from .mcp_polygon_client import _safe_exception
    from .mcp_polygon_models import (
        CandidateRejected,
        CandidateStale,
        McpCallError,
        PipelineError,
        PreparedAsset,
    )
else:
    from mcp_polygon_client import _safe_exception
    from mcp_polygon_models import (
        CandidateRejected,
        CandidateStale,
        McpCallError,
        PipelineError,
        PreparedAsset,
    )


def prepare_batch(context, theme, group, batch_candidates, totals, state):
    """Prepare each candidate, tracking deterministic verification and errors."""
    client = context.client
    converter = context.converter
    converter_fingerprint = context.converter_fingerprint
    template_path = context.template_path
    run_dir = context.run_dir
    args = context.args
    logger = context.logger
    prepare_candidate = context.prepare_candidate
    verify_first_deterministic_render = context.verify_first_deterministic_render
    determinism_verified, consecutive_asset_errors = state
    prepared_assets: list[PreparedAsset] = []
    for candidate in batch_candidates:
        totals["assets_attempted"] += 1
        try:
            prepared = prepare_candidate(
                client,
                candidate=candidate,
                converter=converter,
                converter_fingerprint=converter_fingerprint,
                template_path=template_path,
                run_dir=run_dir,
                transfer_timeout_seconds=args.transfer_timeout_seconds,
                logger=logger,
            )
            if not determinism_verified:
                verify_first_deterministic_render(
                    prepared,
                    converter=converter,
                    template_path=template_path,
                    run_dir=run_dir,
                )
                determinism_verified = True
                logger.emit(
                    "determinism_verified",
                    source_problem_id=candidate.source_problem_id,
                    asset_key=candidate.asset_key,
                    output_sha256=prepared.output_sha256,
                )
            prepared_assets.append(prepared)
            totals["assets_prepared"] += 1
            consecutive_asset_errors = 0
            logger.emit(
                "asset_prepared",
                theme=theme.title,
                group_key=group.group_key,
                source_problem_id=candidate.source_problem_id,
                problem_id=candidate.problem_id,
                asset_key=candidate.asset_key,
                input_sha256=prepared.input_sha256,
                output_sha256=prepared.output_sha256,
                alt_text=prepared.alt_text,
                validation=prepared.validation,
                svg_path=str(prepared.svg_path),
            )
        except (
            CandidateStale,
            CandidateRejected,
            McpCallError,
            httpx.HTTPError,
            OSError,
        ) as exc:
            consecutive_asset_errors = _record_prepare_failure(
                exc,
                context,
                (theme, group, candidate),
                totals,
                consecutive_asset_errors,
            )
    return prepared_assets, determinism_verified, consecutive_asset_errors


def _record_prepare_failure(exc, context, scope, totals, error_count):
    """Record a failed candidate and enforce the consecutive error limit."""
    theme, group, candidate = scope
    if isinstance(exc, (CandidateStale, CandidateRejected)):
        event = "asset_stale" if isinstance(exc, CandidateStale) else "asset_rejected"
        totals["assets_stale" if event == "asset_stale" else "assets_rejected"] += 1
        context.logger.emit(
            event,
            level="warning",
            theme=theme.title,
            group_key=group.group_key,
            source_problem_id=candidate.source_problem_id,
            problem_id=candidate.problem_id,
            asset_key=candidate.asset_key,
            reason=_safe_exception(exc),
        )
        return 0
    totals["asset_errors"] += 1
    error_count += 1
    context.logger.emit(
        "asset_error",
        level="error",
        theme=theme.title,
        group_key=group.group_key,
        source_problem_id=candidate.source_problem_id,
        problem_id=candidate.problem_id,
        asset_key=candidate.asset_key,
        stage="prepare",
        reason=_safe_exception(exc),
    )
    if context.args.max_asset_errors and error_count >= context.args.max_asset_errors:
        raise PipelineError("maximum consecutive asset error count reached") from exc
    return error_count


def apply_batch(
    context, theme, group, prepared_assets, totals, consecutive_asset_errors
):
    """Apply prepared assets or record their dry-run results."""
    apply = context.apply
    client = context.client
    source_site_id = context.source_site_id
    args = context.args
    logger = context.logger
    apply_prepared_asset = context.apply_prepared_asset
    replaced_in_batch = 0
    if apply:
        for prepared in prepared_assets:
            candidate = prepared.candidate
            try:
                source_asset_id, cleanup = apply_prepared_asset(
                    client,
                    source_site_id=source_site_id,
                    prepared=prepared,
                    transfer_timeout_seconds=args.transfer_timeout_seconds,
                    logger=logger,
                )
                replaced_in_batch += 1
                totals["assets_replaced"] += 1
                consecutive_asset_errors = 0
                logger.emit(
                    "asset_replaced",
                    theme=theme.title,
                    group_key=group.group_key,
                    source_problem_id=candidate.source_problem_id,
                    problem_id=candidate.problem_id,
                    asset_key=candidate.asset_key,
                    transformation_target_id=prepared.transformation_target_id,
                    source_asset_id=source_asset_id,
                    output_sha256=prepared.output_sha256,
                    alt_text=prepared.alt_text,
                    cleanup=cleanup,
                )
            except CandidateStale as exc:
                totals["assets_stale"] += 1
                consecutive_asset_errors = 0
                logger.emit(
                    "asset_stale",
                    level="warning",
                    theme=theme.title,
                    group_key=group.group_key,
                    source_problem_id=candidate.source_problem_id,
                    problem_id=candidate.problem_id,
                    asset_key=candidate.asset_key,
                    stage="apply",
                    reason=_safe_exception(exc),
                )
            except (
                McpCallError,
                httpx.HTTPError,
                OSError,
                PipelineError,
            ) as exc:
                totals["asset_errors"] += 1
                consecutive_asset_errors += 1
                logger.emit(
                    "asset_error",
                    level="error",
                    theme=theme.title,
                    group_key=group.group_key,
                    source_problem_id=candidate.source_problem_id,
                    problem_id=candidate.problem_id,
                    asset_key=candidate.asset_key,
                    stage="apply",
                    reason=_safe_exception(exc),
                )
                if (
                    args.max_asset_errors
                    and consecutive_asset_errors >= args.max_asset_errors
                ):
                    raise PipelineError(
                        "maximum consecutive asset error count reached"
                    ) from exc
    else:
        totals["assets_dry_run"] += len(prepared_assets)
    return replaced_in_batch, consecutive_asset_errors
