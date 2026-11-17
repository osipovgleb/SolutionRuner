"""Parse and validate the polygon asset pipeline command line."""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

if __package__:
    from .mcp_polygon_config import (
        DEFAULT_CATALOG_SNAPSHOT_ID,
        DEFAULT_CATEGORY_KEY,
        DEFAULT_CATEGORY_TITLE,
        DEFAULT_MCP_URL,
        DEFAULT_THEME_TITLES,
        EXPECTED_VERTICES_BY_THEME,
    )
else:
    from mcp_polygon_config import (
        DEFAULT_CATALOG_SNAPSHOT_ID,
        DEFAULT_CATEGORY_KEY,
        DEFAULT_CATEGORY_TITLE,
        DEFAULT_MCP_URL,
        DEFAULT_THEME_TITLES,
        EXPECTED_VERTICES_BY_THEME,
    )


def _add_artifact_arguments(parser, script_dir, default_run_dir):
    """Add local output, resume, converter, and template options."""
    parser.add_argument("--run-dir", type=Path, default=default_run_dir)
    parser.add_argument(
        "--resume-from-run",
        type=Path,
        default=None,
        help=(
            "Reuse and validate worklist.json/events.jsonl from a prior run. "
            "Required by rollback."
        ),
    )
    parser.add_argument(
        "--resume-preserve-applied",
        action="store_true",
        help=(
            "Keep successful replacements from the source run while retrying "
            "its rejected assets with a changed converter."
        ),
    )
    parser.add_argument(
        "--converter-path",
        type=Path,
        default=script_dir / "png_to_svg_by_contrast.py",
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        default=script_dir / "template_from_lessons.svg",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the inventory, dry-run, apply, and guarded rollback CLI."""

    script_dir = Path(__file__).resolve().parent
    default_run_dir = (
        Path(os.environ.get("SOLUTION_RUNNER_VAR_DIR", "var"))
        / "mcp-grid-polygon"
        / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    )
    parser = argparse.ArgumentParser(
        description=(
            "Autonomously discover non-rejected grid-polygon PNGs, render SVG, "
            "and optionally attach exact target-scoped MCP transformations."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("inventory", "dry-run", "apply", "rollback"),
        default="dry-run",
    )
    parser.add_argument(
        "--mcp-url",
        default=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
    )
    parser.add_argument("--api-key-env", default="TEACHERHELPER_MCP_API_KEY")
    parser.add_argument("--catalog-snapshot-id", default=DEFAULT_CATALOG_SNAPSHOT_ID)
    parser.add_argument("--confirm-catalog", default=None)
    parser.add_argument("--category-key", default=DEFAULT_CATEGORY_KEY)
    parser.add_argument("--category-title", default=DEFAULT_CATEGORY_TITLE)
    parser.add_argument(
        "--theme",
        action="append",
        dest="theme_titles",
        help="Exact theme title; repeat to override the four default themes.",
    )
    parser.add_argument(
        "--group-key",
        action="append",
        dest="group_keys",
        help="Exact configured source group key; repeat to select more than one group.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Ordered progress checkpoint size; apply mode requires 10.",
    )
    parser.add_argument("--batch-pause-seconds", type=float, default=0.0)
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum active problem chains in the sliding window (1..10).",
    )
    parser.add_argument("--max-tasks", type=int, default=None)
    parser.add_argument("--stop-after-batches", type=int, default=None)
    parser.add_argument(
        "--max-asset-errors",
        type=int,
        default=0,
        help="Stop after this many consecutive errors; 0 keeps skipping and logging.",
    )
    parser.add_argument("--mcp-timeout-seconds", type=float, default=120.0)
    parser.add_argument("--transfer-timeout-seconds", type=float, default=120.0)
    _add_artifact_arguments(parser, script_dir, default_run_dir)
    return parser


def _validate_cli_args(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Reject ambiguous or unsafe local CLI combinations."""

    if args.theme_titles is None:
        args.theme_titles = list(DEFAULT_THEME_TITLES)
    if any(theme not in EXPECTED_VERTICES_BY_THEME for theme in args.theme_titles):
        parser.error(
            f"themes must be selected from {sorted(EXPECTED_VERTICES_BY_THEME)}"
        )
    if args.group_keys is not None and len(set(args.group_keys)) != len(
        args.group_keys
    ):
        parser.error("--group-key values must be unique")
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.batch_pause_seconds < 0:
        parser.error("--batch-pause-seconds cannot be negative")
    if not 1 <= args.max_workers <= 10:
        parser.error("--max-workers must be between 1 and 10")
    if (
        args.mode in {"dry-run", "apply"}
        and args.max_workers > 1
        and args.batch_pause_seconds
    ):
        parser.error("concurrent mode requires --batch-pause-seconds 0")
    if (
        args.mode in {"dry-run", "apply"}
        and args.max_workers > 1
        and args.max_asset_errors
    ):
        parser.error("--max-asset-errors requires --max-workers 1")
    if args.max_tasks is not None and args.max_tasks <= 0:
        parser.error("--max-tasks must be positive")
    if args.stop_after_batches is not None and args.stop_after_batches <= 0:
        parser.error("--stop-after-batches must be positive")
    if args.max_asset_errors < 0:
        parser.error("--max-asset-errors cannot be negative")
    if args.mode == "rollback" and args.resume_from_run is None:
        parser.error("rollback mode requires --resume-from-run")
    if args.mode == "inventory" and args.resume_from_run is not None:
        parser.error("inventory mode cannot use --resume-from-run")
    if args.resume_preserve_applied and (
        args.mode != "apply" or args.resume_from_run is None
    ):
        parser.error(
            "--resume-preserve-applied requires apply mode and --resume-from-run"
        )
