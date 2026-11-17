"""Run one registered source group through its deterministic repair workflow."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from solution_runner.group_inventory_store import GroupInventoryStore

from ..core.local_inventory import load_group_inventory
from ..core.models import (
    PreparedFigure,
    PreparedGridPolygon,
    ProblemStageResult,
)
from .asset_preparation import execute_image_preparation, prepare_existing_svg
from .helpers_runtime import run_helpers_stage
from .inventory import (
    GroupInventory,
    discover_group_inventory,
    discover_targeted_inventory,
)
from .launcher_args import _parser as _argument_parser
from .launcher_args import _validated_args
from .launcher_records import (
    _ordered_prepared,
    _scope,
    _selected_inventory,
)
from .launcher_stages import _run_content_rule_stages, _run_stages, _StageContext
from .manifest import FrozenRunScope, read_prepared_manifest, write_prepared_manifest
from .mcp_runtime import DEFAULT_MCP_URL, JsonRpcMcpGateway
from .progress import ProgressReporter
from .ring_asset_preparation import prepare_ring_assets
from .solution_runtime import run_solution_stage

_parser = _argument_parser

DEFAULT_OUTPUT_ROOT = (
    Path(os.environ.get("SOLUTION_RUNNER_VAR_DIR", "var")) / "grid-polygon" / "runs"
)


@dataclass(frozen=True)
class LauncherDependencies:
    """Inject orchestration boundaries for deterministic local tests."""

    gateway_factory: Callable[[str], Any]
    inventory: Callable[..., GroupInventory]
    image_executor: Callable[[tuple[str, ...]], int]
    prepare_images: Callable[..., tuple[PreparedGridPolygon, ...]]
    prepare_rings: Callable[..., tuple[PreparedFigure, ...]]
    prepare_existing: Callable[..., PreparedGridPolygon]
    solution_stage: Callable[..., tuple[ProblemStageResult, ...]]
    helpers_stage: Callable[..., tuple[ProblemStageResult, ...]]
    output_root: Path
    now: Callable[[], datetime]
    content_rule_stage: Callable[..., tuple[ProblemStageResult, ...]] | None = None
    targeted_inventory: Callable[..., GroupInventory] | None = None


def _execute(command: tuple[str, ...]) -> int:
    """Run one external converter command without shell interpolation."""

    return subprocess.run(command, check=False).returncode


def _run_content_rule_stage(
    *args: Any, **kwargs: Any
) -> tuple[ProblemStageResult, ...]:
    """Load the content-rule runtime only for explicitly configured groups."""

    from ..core.content_runtime import run_content_rule_stage

    return run_content_rule_stage(*args, **kwargs)


def _default_dependencies() -> LauncherDependencies:
    """Return production dependencies while leaving gateway creation lazy."""

    return LauncherDependencies(
        gateway_factory=lambda api_key: JsonRpcMcpGateway(
            url=os.environ.get("TEACHERHELPER_MCP_URL", DEFAULT_MCP_URL),
            api_key=api_key,
        ),
        inventory=discover_group_inventory,
        targeted_inventory=discover_targeted_inventory,
        image_executor=_execute,
        prepare_images=execute_image_preparation,
        prepare_rings=prepare_ring_assets,
        prepare_existing=prepare_existing_svg,
        solution_stage=run_solution_stage,
        helpers_stage=run_helpers_stage,
        output_root=DEFAULT_OUTPUT_ROOT,
        now=lambda: datetime.now(UTC),
        content_rule_stage=_run_content_rule_stage,
    )


def _api_key() -> str:
    """Return the terminal-local MCP key without logging it."""

    value = os.environ.get("TEACHERHELPER_MCP_API_KEY", "").strip()
    if value:
        return value
    return getpass.getpass("TEACHERHELPER_MCP_API_KEY: ").strip()


def _prepare_existing_targets(context, args, existing_targets, apply_images):
    active, gateway, profile, run_dir = (
        context.active,
        context.gateway,
        context.profile,
        context.run_dir,
    )

    def prepare_target(
        target: Any,
    ) -> tuple[PreparedGridPolygon | None, dict[str, str] | None]:
        """Prepare one existing SVG and convert its failure to ordered evidence."""

        try:
            return (
                active.prepare_existing(
                    gateway,
                    target,
                    artifact_dir=run_dir / "existing-svg",
                    profile=profile,
                    apply=apply_images,
                ),
                None,
            )
        except Exception as exc:  # noqa: BLE001 - isolate one existing SVG.
            return (
                None,
                {
                    "problem_id": target.problem_id,
                    "source_problem_id": target.source_problem_id,
                    "error": " ".join(str(exc).split())[:2000],
                },
            )

    if args.max_workers == 1:
        existing_results = tuple(map(prepare_target, existing_targets))
    else:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            existing_results = tuple(executor.map(prepare_target, existing_targets))
    records = []
    image_errors = []
    for record, error in existing_results:
        if record is not None:
            records.append(record)
        if error is not None:
            image_errors.append(error)
    return records, image_errors


def _prepared_records(
    context: _StageContext, args: argparse.Namespace, inventory: GroupInventory
) -> tuple[PreparedFigure, ...]:
    """Load a resume manifest or prepare and freeze the selected image scope."""
    active, gateway, profile = context.active, context.gateway, context.profile
    run_dir, reporter = context.run_dir, context.reporter

    manifest_path = run_dir / "prepared-manifest.json"
    apply_images = args.apply and not args.helpers_from_existing_solution
    if args.resume_solutions or args.resume_images:
        expected = FrozenRunScope(
            catalog_snapshot_id=profile.catalog_snapshot_id,
            snapshot_theme_id=profile.snapshot_theme_id,
            source_group_id=profile.source_group_id,
            group_key=profile.group_key,
            target_problem_ids=tuple(target.problem_id for target in inventory.targets),
        )
        return read_prepared_manifest(
            manifest_path,
            expected_scope=expected,
            allow_target_subset=True,
        )
    records: list[PreparedFigure] = []
    image_errors: list[dict[str, str]] = []
    if profile.geometry_kind == "ring":
        ring_run_dir = run_dir / "images"
        records.extend(
            active.prepare_rings(
                gateway,
                profile=profile,
                run_dir=ring_run_dir,
                expected_targets=inventory.targets,
                apply=apply_images,
                batch_size=args.batch_size,
                batch_pause_seconds=args.batch_pause_seconds,
                max_workers=args.max_workers,
                reporter=reporter,
            )
        )
        ring_errors_path = ring_run_dir / "image-errors.json"
        if ring_errors_path.is_file():
            raw_ring_errors = json.loads(ring_errors_path.read_text(encoding="utf-8"))
            if isinstance(raw_ring_errors, list):
                image_errors.extend(
                    item for item in raw_ring_errors if isinstance(item, dict)
                )
    elif inventory.png_targets:
        records.extend(
            active.prepare_images(
                active.image_executor,
                profile=profile,
                run_dir=run_dir / "images",
                expected_targets=inventory.png_targets,
                apply=apply_images,
                batch_size=args.batch_size,
                batch_pause_seconds=args.batch_pause_seconds,
            )
        )
    existing_targets = () if profile.geometry_kind == "ring" else inventory.svg_targets

    existing_records, existing_errors = _prepare_existing_targets(
        context, args, existing_targets, apply_images
    )
    records.extend(existing_records)
    image_errors.extend(existing_errors)
    prepared = _ordered_prepared(inventory, tuple(records))
    write_prepared_manifest(manifest_path, _scope(profile, prepared), prepared)
    (run_dir / "image-errors.json").write_text(
        json.dumps(image_errors, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return prepared


def _discover_targets(context, parser, args):
    active, gateway, profile = context.active, context.gateway, context.profile
    targeted, reporter = context.targeted, context.reporter
    discovery_label = (
        "TARGET SELECTION"
        if targeted
        else ("LOCAL INVENTORY" if args.inventory_db else "INVENTORY")
    )
    reporter.group(
        profile.theme_title,
        profile.group_key,
        f"{discovery_label} STARTED",
        stage="target_selection" if targeted else "inventory",
    )
    if args.inventory_db:
        full_inventory = load_group_inventory(
            GroupInventoryStore(args.inventory_db),
            profile,
            apply_solution_scope=not targeted
            and not args.helpers_from_existing_solution,
        )
    elif targeted:
        if active.targeted_inventory is None:
            raise ValueError("targeted inventory dependency is unavailable")
        full_inventory = active.targeted_inventory(
            gateway,
            profile,
            source_problem_ids=tuple(args.only_source_problem_id or ()),
            problem_ids=tuple(args.only_problem_id or ()),
            max_workers=args.max_workers,
        )
    else:
        full_inventory = active.inventory(
            gateway,
            profile,
            max_workers=args.max_workers,
        )
    inventory = _selected_inventory(parser, args, full_inventory)
    if args.exclude_parent_problem:
        parent_problem_id = full_inventory.targets[0].problem_id
        inventory = GroupInventory(
            targets=tuple(
                target
                for target in inventory.targets
                if target.problem_id != parent_problem_id
            ),
            png_targets=(),
            svg_targets=(),
        )
    reporter.group(
        profile.theme_title,
        profile.group_key,
        (
            f"{discovery_label} COMPLETED  TARGETS {len(inventory.targets)}  "
            f"PNG {len(inventory.png_targets)}  SVG {len(inventory.svg_targets)}"
        ),
        severity="success",
        stage="target_selection" if targeted else "inventory",
        details={
            "targets": len(inventory.targets),
            "png": len(inventory.png_targets),
            "svg": len(inventory.svg_targets),
        },
    )
    return full_inventory, inventory


def main(
    argv: list[str] | None = None,
    *,
    deps: LauncherDependencies | None = None,
) -> int:
    """Run one explicit group and return zero even with isolated target errors."""

    parser, args, profile = _validated_args(argv)
    active = deps or _default_dependencies()
    api_key = _api_key()
    if not api_key:
        parser.error("MCP API key is required")
    gateway = active.gateway_factory(api_key)
    try:
        timestamp = active.now().astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
        resume_dir = args.resume_solutions or args.resume_images
        run_dir = (
            resume_dir.resolve()
            if resume_dir
            else (
                active.output_root / f"{timestamp}-group-{profile.group_key}"
            ).resolve()
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        internal_path = run_dir / "internal.jsonl"
        with internal_path.open("a", encoding="utf-8") as internal:
            reporter = ProgressReporter(
                console=sys.stdout,
                internal=internal,
                color=True,
            )
            targeted = bool(args.only_source_problem_id or args.only_problem_id)
            stage_context = _StageContext(
                active=active,
                gateway=gateway,
                profile=profile,
                run_dir=run_dir,
                apply=args.apply,
                targeted=targeted,
                reporter=reporter,
                max_workers=args.max_workers,
            )
            full_inventory, inventory = _discover_targets(stage_context, parser, args)
            if profile.workflow_kind == "content_rule":
                _run_content_rule_stages(
                    stage_context,
                    args,
                    full_inventory,
                    inventory,
                )
            else:
                prepared = (
                    ()
                    if args.helpers_from_existing_solution
                    else _prepared_records(stage_context, args, inventory)
                )
                _run_stages(
                    stage_context,
                    inventory,
                    prepared,
                    helpers_from_existing_solution=args.helpers_from_existing_solution,
                    force_apply=args.force_apply,
                )
        return 0
    finally:
        close = getattr(gateway, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    raise SystemExit(main())
