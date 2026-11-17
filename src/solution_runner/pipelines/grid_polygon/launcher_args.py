"""Parse and validate launcher scope and execution arguments."""

import argparse
from dataclasses import replace
from pathlib import Path

from solution_runner.group_inventory_store import GroupInventoryStore

from ..core.group_profiles import get_group_profile
from ..core.models import GroupProfile


def _parser() -> argparse.ArgumentParser:
    """Build the explicit-group command-line contract."""

    parser = argparse.ArgumentParser(
        description="Run one registered source group through its deterministic repair workflow."
    )
    parser.add_argument("--group", required=True)
    parser.add_argument("--confirm-catalog", required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--force-apply",
        action="store_true",
        help="write one selected task even when its prepared content already matches",
    )
    parser.add_argument(
        "--existing-solution-policy",
        choices=("preserve", "rewrite"),
        help="override the registered profile's handling of an existing solution",
    )
    parser.add_argument(
        "--inventory-db",
        type=Path,
        help="use the initialized local group index instead of repeating MCP discovery",
    )
    parser.add_argument("--resume-images", type=Path)
    parser.add_argument("--resume-solutions", type=Path)
    parser.add_argument(
        "--helpers-from-existing-solution",
        action="store_true",
        help=(
            "do not inspect conditions or rewrite content; set Helpers ready only "
            "where stored solution and answer sections are non-empty"
        ),
    )
    parser.add_argument("--only-source-problem-id", action="append")
    parser.add_argument(
        "--only-problem-id", action="append", help="select by internal problem UUID"
    )
    parser.add_argument(
        "--exclude-parent-problem",
        action="store_true",
        help="run every content-rule task except the first canonical parent",
    )
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--batch-pause-seconds", type=float, default=0.0)
    parser.add_argument("--max-workers", type=int, default=10)
    return parser


def _validated_args(
    argv: list[str] | None,
) -> tuple[argparse.ArgumentParser, argparse.Namespace, GroupProfile]:
    """Parse arguments and reject unsafe scope or batching combinations."""

    parser = _parser()
    args = parser.parse_args(argv)
    try:
        profile = get_group_profile(args.group)
    except KeyError:
        if not (args.helpers_from_existing_solution and args.inventory_db):
            raise
        snapshot = GroupInventoryStore(args.inventory_db).get(args.group)
        if snapshot is None or snapshot.status != "ready":
            parser.error("manual Helpers requires a ready local inventory")
        profile = GroupProfile(
            catalog_snapshot_id=snapshot.catalog_snapshot_id,
            snapshot_theme_id="manual",
            source_group_id=snapshot.source_group_id,
            group_key=args.group,
            group_order_index=0,
            theme_title=f"Группа {args.group}",
            theme_order_index=0,
            expected_vertices=None,
            strategy_key=None,
        )
    if args.confirm_catalog != profile.catalog_snapshot_id:
        parser.error("--confirm-catalog does not match the selected group profile")
    if args.force_apply and not args.apply:
        parser.error("--force-apply requires --apply")
    if args.existing_solution_policy:
        profile = replace(
            profile, existing_solution_policy=args.existing_solution_policy
        )
    if args.force_apply:
        profile = replace(profile, existing_solution_policy="rewrite")
    if args.resume_images and args.resume_solutions:
        parser.error("choose only one resume mode")
    if args.only_source_problem_id and args.only_problem_id:
        parser.error("choose only one problem selector")
    if args.exclude_parent_problem and (
        args.only_source_problem_id or args.only_problem_id
    ):
        parser.error(
            "--exclude-parent-problem cannot be combined with problem selectors"
        )
    if args.exclude_parent_problem and profile.workflow_kind != "content_rule":
        parser.error("--exclude-parent-problem requires a content-rule group")
    if args.helpers_from_existing_solution and (
        args.resume_images or args.resume_solutions
    ):
        parser.error(
            "--helpers-from-existing-solution cannot be combined with resume modes"
        )
    selected_ids = args.only_problem_id or args.only_source_problem_id or []
    if len(selected_ids) != len(set(selected_ids)):
        parser.error("problem selectors must be unique")
    if profile.workflow_kind == "content_rule" and args.resume_images:
        parser.error("content-rule groups resume with --resume-solutions")
    if args.batch_size <= 0 or args.batch_pause_seconds < 0:
        parser.error("batch size must be positive and pause cannot be negative")
    if not 1 <= args.max_workers <= 10:
        parser.error("--max-workers must be between 1 and 10")
    return parser, args, profile
