"""Run ordered polygon asset groups in serial or bounded parallel mode."""

from __future__ import annotations

import time
from types import SimpleNamespace

if __package__:
    from . import (
        mcp_polygon_batch,
        mcp_polygon_parallel,
        mcp_polygon_reporting,
    )
    from .mcp_polygon_processing import (
        _assert_locked_inputs,
        _problem_batches,
    )
else:
    import mcp_polygon_batch
    import mcp_polygon_parallel
    import mcp_polygon_reporting
    from mcp_polygon_processing import (
        _assert_locked_inputs,
        _problem_batches,
    )


def process_groups(context, processing_scope):
    """Process selected groups while preserving checkpoint and task ordering."""
    logger = context.logger
    converter_path = context.converter_path
    converter_fingerprint = context.converter_fingerprint
    template_path = context.template_path
    template_fingerprint = context.template_fingerprint
    inventory_by_group = context.inventory_by_group
    args = context.args
    client = context.client
    source_site_id = context.source_site_id
    converter = context.converter
    run_dir = context.run_dir
    apply = context.apply
    prepare_candidate = context.prepare_candidate
    apply_prepared_asset = context.apply_prepared_asset
    verify_first_deterministic_render = context.verify_first_deterministic_render
    _ProcessingContext = context.processing_context_type
    totals = context.totals
    stop_requested = False
    global_tasks_seen = 0
    batches_seen = 0
    consecutive_asset_errors = 0
    determinism_verified = False
    for theme, groups in processing_scope:
        if stop_requested:
            break
        logger.emit(
            "theme_start",
            theme=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            groups=len(groups),
        )
        for group in groups:
            if stop_requested:
                break
            logger.emit(
                "group_transition",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
            )
            _assert_locked_inputs(
                converter_path=converter_path,
                converter_fingerprint=converter_fingerprint,
                template_path=template_path,
                template_fingerprint=template_fingerprint,
            )
            inventory = inventory_by_group[group.source_group_id]
            logger.emit(
                "group_opened",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
                tasks=inventory.counts.get("png_tasks", 0),
                assets=inventory.counts.get("png_assets", 0),
            )
            logger.emit(
                "group_inventory",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
                tasks=inventory.counts.get("png_tasks", 0),
                assets=inventory.counts.get("png_assets", 0),
                counts=inventory.counts,
                non_svg_content_types=inventory.non_svg_content_types,
                source_problem_ids=inventory.png_source_problem_ids,
            )
            if not inventory.candidates:
                continue

            if args.max_workers > 1:
                (
                    global_tasks_seen,
                    batches_seen,
                    consecutive_asset_errors,
                    determinism_verified,
                    stop_requested,
                ) = mcp_polygon_parallel.process_parallel_group(
                    context,
                    theme,
                    group,
                    inventory,
                    (
                        global_tasks_seen,
                        batches_seen,
                        consecutive_asset_errors,
                        determinism_verified,
                        stop_requested,
                    ),
                )
                if stop_requested:
                    break
                continue

            batches = list(_problem_batches(inventory.candidates, args.batch_size))
            for local_batch_index, batch_candidates in enumerate(batches, start=1):
                if stop_requested:
                    break
                problem_order = list(
                    dict.fromkeys(c.problem_id for c in batch_candidates)
                )
                if args.max_tasks is not None:
                    remaining = args.max_tasks - global_tasks_seen
                    if remaining <= 0:
                        stop_requested = True
                        break
                    allowed_problem_ids = set(problem_order[:remaining])
                    batch_candidates = [
                        candidate
                        for candidate in batch_candidates
                        if candidate.problem_id in allowed_problem_ids
                    ]
                    problem_order = problem_order[:remaining]
                global_tasks_seen += len(problem_order)
                batches_seen += 1
                logger.emit(
                    "batch_start",
                    theme=theme.title,
                    group_key=group.group_key,
                    batch=batches_seen,
                    group_batch=local_batch_index,
                    tasks=len(problem_order),
                    assets=len(batch_candidates),
                    source_problem_ids=list(
                        dict.fromkeys(c.source_problem_id for c in batch_candidates)
                    ),
                )

                batch_context = SimpleNamespace(
                    client=client,
                    converter=converter,
                    converter_fingerprint=converter_fingerprint,
                    template_path=template_path,
                    run_dir=run_dir,
                    args=args,
                    logger=logger,
                    prepare_candidate=prepare_candidate,
                    verify_first_deterministic_render=verify_first_deterministic_render,
                    apply=apply,
                    source_site_id=source_site_id,
                    apply_prepared_asset=apply_prepared_asset,
                )
                prepared_assets, determinism_verified, consecutive_asset_errors = (
                    mcp_polygon_batch.prepare_batch(
                        batch_context,
                        theme,
                        group,
                        batch_candidates,
                        totals,
                        (determinism_verified, consecutive_asset_errors),
                    )
                )

                replaced_in_batch, consecutive_asset_errors = (
                    mcp_polygon_batch.apply_batch(
                        batch_context,
                        theme,
                        group,
                        prepared_assets,
                        totals,
                        consecutive_asset_errors,
                    )
                )

                logger.emit(
                    "batch_complete",
                    theme=theme.title,
                    group_key=group.group_key,
                    batch=batches_seen,
                    tasks=len(problem_order),
                    assets=len(batch_candidates),
                    prepared=len(prepared_assets),
                    replaced=replaced_in_batch,
                )
                mcp_polygon_reporting.write_progress(
                    run_dir,
                    args,
                    theme,
                    group,
                    (batches_seen, global_tasks_seen),
                    totals,
                )
                if apply and batch_candidates:
                    logger.emit(
                        "batch_pause",
                        theme=theme.title,
                        group_key=group.group_key,
                        batch=batches_seen,
                        seconds=args.batch_pause_seconds,
                    )
                    time.sleep(args.batch_pause_seconds)
                if (
                    args.stop_after_batches is not None
                    and batches_seen >= args.stop_after_batches
                ):
                    stop_requested = True
                if args.max_tasks is not None and global_tasks_seen >= args.max_tasks:
                    stop_requested = True

        logger.emit("theme_complete", theme=theme.title)
    return global_tasks_seen, batches_seen, determinism_verified, stop_requested
