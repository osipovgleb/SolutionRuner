"""Process one polygon group with a bounded worker pool."""

from __future__ import annotations

from functools import partial

if __package__:
    from . import mcp_polygon_processing, mcp_polygon_reporting
    from .mcp_polygon_models import _CandidateOutcome
    from .mcp_polygon_processing import _problem_units, _process_problem_unit
    from .mcp_polygon_util import _bounded_map_ordered
else:
    import mcp_polygon_processing
    import mcp_polygon_reporting
    from mcp_polygon_models import _CandidateOutcome
    from mcp_polygon_processing import _problem_units, _process_problem_unit
    from mcp_polygon_util import _bounded_map_ordered


def process_parallel_group(context, theme, group, inventory, state):
    """Process and checkpoint one group's parallel candidate window."""
    args = context.args
    logger = context.logger
    client = context.client
    source_site_id = context.source_site_id
    converter = context.converter
    converter_fingerprint = context.converter_fingerprint
    template_path = context.template_path
    run_dir = context.run_dir
    apply = context.apply
    determinism_gate = context.determinism_gate
    prepare_candidate = context.prepare_candidate
    apply_prepared_asset = context.apply_prepared_asset
    totals = context.totals
    _ProcessingContext = context.processing_context_type
    (
        global_tasks_seen,
        batches_seen,
        consecutive_asset_errors,
        determinism_verified,
        stop_requested,
    ) = state
    problem_units = _problem_units(inventory.candidates)
    if args.max_tasks is not None:
        remaining_tasks = args.max_tasks - global_tasks_seen
        if remaining_tasks <= 0:
            stop_requested = True
            return (
                global_tasks_seen,
                batches_seen,
                consecutive_asset_errors,
                determinism_verified,
                stop_requested,
            )
        problem_units = problem_units[:remaining_tasks]
    if args.stop_after_batches is not None:
        remaining_checkpoints = args.stop_after_batches - batches_seen
        if remaining_checkpoints <= 0:
            stop_requested = True
            return (
                global_tasks_seen,
                batches_seen,
                consecutive_asset_errors,
                determinism_verified,
                stop_requested,
            )
        problem_units = problem_units[: remaining_checkpoints * args.batch_size]
    if not problem_units:
        return (
            global_tasks_seen,
            batches_seen,
            consecutive_asset_errors,
            determinism_verified,
            stop_requested,
        )
    logger.emit(
        "worker_pool_start",
        theme=theme.title,
        group_key=group.group_key,
        tasks=len(problem_units),
        max_workers=args.max_workers,
    )
    processing_context = _ProcessingContext(
        client=client,
        source_site_id=source_site_id,
        converter=converter,
        converter_fingerprint=converter_fingerprint,
        template_path=template_path,
        run_dir=run_dir,
        transfer_timeout_seconds=args.transfer_timeout_seconds,
        logger=logger,
        apply=apply,
        determinism_gate=determinism_gate,
        prepare_candidate=prepare_candidate,
        apply_prepared_asset=apply_prepared_asset,
    )
    process_unit = partial(
        _process_problem_unit,
        processing_context,
    )
    preflight_outcomes: list[tuple[_CandidateOutcome, ...]] = []
    remaining_units = problem_units
    while remaining_units and not determinism_gate.verified:
        preflight_outcomes.append(process_unit(remaining_units[0]))
        remaining_units = remaining_units[1:]
    problem_outcomes = (
        *preflight_outcomes,
        *_bounded_map_ordered(
            remaining_units,
            process_unit,
            max_workers=args.max_workers,
        ),
    )
    determinism_verified = determinism_verified or determinism_gate.verified
    for checkpoint_start in range(
        0,
        len(problem_outcomes),
        args.batch_size,
    ):
        checkpoint_units = problem_outcomes[
            checkpoint_start : checkpoint_start + args.batch_size
        ]
        outcomes = tuple(
            outcome for unit_outcomes in checkpoint_units for outcome in unit_outcomes
        )
        global_tasks_seen += len(checkpoint_units)
        batches_seen += 1
        prepared_count, replaced_count, consecutive_asset_errors = (
            mcp_polygon_processing.account_outcomes(
                totals, outcomes, consecutive_asset_errors
            )
        )
        logger.emit(
            "batch_complete",
            theme=theme.title,
            group_key=group.group_key,
            batch=batches_seen,
            tasks=len(checkpoint_units),
            assets=len(outcomes),
            prepared=prepared_count,
            replaced=replaced_count,
        )
        mcp_polygon_reporting.write_progress(
            run_dir,
            args,
            theme,
            group,
            (batches_seen, global_tasks_seen),
            totals,
        )
    if args.stop_after_batches is not None and batches_seen >= args.stop_after_batches:
        stop_requested = True
    if args.max_tasks is not None and global_tasks_seen >= args.max_tasks:
        stop_requested = True
    return (
        global_tasks_seen,
        batches_seen,
        consecutive_asset_errors,
        determinism_verified,
        stop_requested,
    )
