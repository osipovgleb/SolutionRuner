"""Run one registered source group through its deterministic repair workflow."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

from solution_runner.group_inventory_store import GroupInventoryStore

from .asset_preparation import execute_image_preparation, prepare_existing_svg
from ..core.group_profiles import get_group_profile
from .helpers_runtime import run_helpers_stage, verify_existing_solutions
from .inventory import (
    GroupInventory,
    discover_group_inventory,
    discover_targeted_inventory,
)
from .manifest import FrozenRunScope, read_prepared_manifest, write_prepared_manifest
from .mcp_runtime import DEFAULT_MCP_URL, JsonRpcMcpGateway
from ..core.models import GroupProfile, PreparedFigure, PreparedGridPolygon, ProblemStageResult
from ..core.local_inventory import load_group_inventory
from .progress import ProgressReporter
from .ring_asset_preparation import prepare_ring_assets
from .solution_runtime import run_solution_stage
from .strategies import get_solution_strategy


DEFAULT_OUTPUT_ROOT = Path(
    os.environ.get("SOLUTION_RUNNER_VAR_DIR", "var")
) / "grid-polygon" / "runs"


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


@dataclass(frozen=True)
class _StageContext:
    """Carry shared dependencies for solution and Helpers orchestration."""

    active: LauncherDependencies
    gateway: Any
    profile: GroupProfile
    run_dir: Path
    apply: bool
    targeted: bool
    reporter: ProgressReporter
    max_workers: int


def _execute(command: tuple[str, ...]) -> int:
    """Run one external converter command without shell interpolation."""

    return subprocess.run(command, check=False).returncode


def _run_content_rule_stage(*args: Any, **kwargs: Any) -> tuple[ProblemStageResult, ...]:
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


def _parser() -> argparse.ArgumentParser:
    """Build the explicit-group command-line contract."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--group", required=True)
    parser.add_argument("--confirm-catalog", required=True)
    parser.add_argument("--apply", action="store_true")
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
            "do not rewrite solutions; set Helpers ready only where the existing "
            "single calculation ends with the stored numeric answer"
        ),
    )
    parser.add_argument("--only-source-problem-id", action="append")
    parser.add_argument("--only-problem-id", action="append", help="select by internal problem UUID")
    parser.add_argument(
        "--exclude-parent-problem",
        action="store_true",
        help="run every content-rule task except the first canonical parent",
    )
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--batch-pause-seconds", type=float, default=0.0)
    parser.add_argument("--max-workers", type=int, default=10)
    return parser


def _api_key() -> str:
    """Return the terminal-local MCP key without logging it."""

    value = os.environ.get("TEACHERHELPER_MCP_API_KEY", "").strip()
    if value:
        return value
    return getpass.getpass("TEACHERHELPER_MCP_API_KEY: ").strip()


def _scope(profile: Any, prepared: tuple[PreparedFigure, ...]) -> FrozenRunScope:
    """Build the exact prepared-record scope stored for resume."""

    return FrozenRunScope(
        catalog_snapshot_id=profile.catalog_snapshot_id,
        snapshot_theme_id=profile.snapshot_theme_id,
        source_group_id=profile.source_group_id,
        group_key=profile.group_key,
        target_problem_ids=tuple(record.problem_id for record in prepared),
    )


def _ordered_prepared(
    inventory: GroupInventory,
    records: tuple[PreparedFigure, ...],
) -> tuple[PreparedFigure, ...]:
    """Return successful prepared records in frozen group order."""

    by_problem_id = {record.problem_id: record for record in records}
    return tuple(
        by_problem_id[target.problem_id]
        for target in inventory.targets
        if target.problem_id in by_problem_id
    )


def _write_results(path: Path, results: tuple[ProblemStageResult, ...]) -> None:
    """Persist content-free terminal stage results."""

    path.write_text(
        json.dumps(
            [asdict(result) for result in results],
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )


def _validated_args(
    argv: list[str] | None,
) -> tuple[argparse.ArgumentParser, argparse.Namespace, GroupProfile]:
    """Parse arguments and reject unsafe scope or batching combinations."""

    parser = _parser()
    args = parser.parse_args(argv)
    profile = get_group_profile(args.group)
    if args.confirm_catalog != profile.catalog_snapshot_id:
        parser.error("--confirm-catalog does not match the selected group profile")
    if args.resume_images and args.resume_solutions:
        parser.error("choose only one resume mode")
    if args.only_source_problem_id and args.only_problem_id:
        parser.error("choose only one problem selector")
    if args.exclude_parent_problem and (
        args.only_source_problem_id or args.only_problem_id
    ):
        parser.error("--exclude-parent-problem cannot be combined with problem selectors")
    if args.exclude_parent_problem and profile.workflow_kind != "content_rule":
        parser.error("--exclude-parent-problem requires a content-rule group")
    if args.helpers_from_existing_solution and profile.workflow_kind != "content_rule":
        parser.error("--helpers-from-existing-solution requires a content-rule group")
    if args.helpers_from_existing_solution and (args.resume_images or args.resume_solutions):
        parser.error("--helpers-from-existing-solution cannot be combined with resume modes")
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


def _selected_inventory(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    inventory: GroupInventory,
) -> GroupInventory:
    """Narrow the frozen inventory to optional exact source problems."""

    if args.only_source_problem_id and args.only_problem_id:
        parser.error("choose only one problem selector")
    if not args.only_source_problem_id and not args.only_problem_id:
        return inventory
    field = "problem_id" if args.only_problem_id else "source_problem_id"
    requested_ids = set(args.only_problem_id or args.only_source_problem_id)
    matches = tuple(
        target
        for target in inventory.targets
        if getattr(target, field) in requested_ids
    )
    if (
        len(matches) != len(requested_ids)
        or {getattr(target, field) for target in matches} != requested_ids
    ):
        parser.error(f"--only-{field.replace('_', '-')} is outside the frozen group scope")
    selected_ids = {target.problem_id for target in matches}
    return GroupInventory(
        targets=matches,
        png_targets=tuple(
            target
            for target in inventory.png_targets
            if target.problem_id in selected_ids
        ),
        svg_targets=tuple(
            target
            for target in inventory.svg_targets
            if target.problem_id in selected_ids
        ),
    )


def _prepared_records(
    active: LauncherDependencies,
    args: argparse.Namespace,
    gateway: Any,
    profile: GroupProfile,
    inventory: GroupInventory,
    run_dir: Path,
    reporter: ProgressReporter,
) -> tuple[PreparedFigure, ...]:
    """Load a resume manifest or prepare and freeze the selected image scope."""

    manifest_path = run_dir / "prepared-manifest.json"
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
                apply=args.apply,
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
                apply=args.apply,
                batch_size=args.batch_size,
                batch_pause_seconds=args.batch_pause_seconds,
            )
        )
    existing_targets = (
        () if profile.geometry_kind == "ring" else inventory.svg_targets
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
                    apply=args.apply,
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
    for record, error in existing_results:
        if record is not None:
            records.append(record)
        if error is not None:
            image_errors.append(error)
    prepared = _ordered_prepared(inventory, tuple(records))
    write_prepared_manifest(manifest_path, _scope(profile, prepared), prepared)
    (run_dir / "image-errors.json").write_text(
        json.dumps(image_errors, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return prepared


def _run_stages(
    context: _StageContext,
    inventory: GroupInventory,
    prepared: tuple[PreparedFigure, ...],
) -> None:
    """Run solution and Helpers stages and persist their terminal summary."""

    if context.profile.strategy_key is None:
        raise ValueError("geometry workflow requires strategy_key")
    strategy = get_solution_strategy(context.profile.strategy_key)
    solution_results = context.active.solution_stage(
        context.gateway,
        prepared,
        context.profile,
        strategy,
        context.reporter,
        apply=context.apply,
        max_workers=context.max_workers,
    )
    helpers_results = context.active.helpers_stage(
        context.gateway,
        solution_results,
        context.profile,
        context.reporter,
        apply=context.apply,
        max_workers=context.max_workers,
    )
    _write_results(context.run_dir / "solution-results.json", solution_results)
    _write_results(context.run_dir / "helpers-results.json", helpers_results)
    failed = sum(
        result.status == "failed" for result in (*solution_results, *helpers_results)
    )
    summary = {
        "schema_version": 1,
        "status": "completed_with_errors" if failed else "completed",
        "group_key": context.profile.group_key,
        "strategy_key": context.profile.strategy_key,
        "targets": len(inventory.targets),
        "prepared": len(prepared),
        "failed_stage_results": failed,
        "apply": context.apply,
        "targeted": context.targeted,
    }
    (context.run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _run_content_rule_stages(
    context: _StageContext,
    args: argparse.Namespace,
    full_inventory: GroupInventory,
    inventory: GroupInventory,
) -> None:
    """Run one non-geometric content rule through shared reporting and Helpers."""

    if not full_inventory.targets:
        raise ValueError("content-rule group has no asset source target")
    if context.active.content_rule_stage is None:
        raise ValueError("content-rule runtime is unavailable")
    if args.helpers_from_existing_solution:
        solution_results = verify_existing_solutions(
            context.gateway,
            inventory.targets,
            context.profile,
            context.reporter,
        )
    else:
        solution_results = context.active.content_rule_stage(
            context.gateway,
            inventory.targets,
            full_inventory.targets[0],
            context.profile,
            context.reporter,
            run_dir=context.run_dir,
            resume=bool(args.resume_solutions),
            apply=context.apply,
            batch_size=args.batch_size,
            batch_pause_seconds=args.batch_pause_seconds,
            max_workers=context.max_workers,
        )
    helpers_results = context.active.helpers_stage(
        context.gateway,
        solution_results,
        context.profile,
        context.reporter,
        apply=context.apply,
        max_workers=context.max_workers,
    )
    _write_results(context.run_dir / "solution-results.json", solution_results)
    _write_results(context.run_dir / "helpers-results.json", helpers_results)
    failed = sum(
        result.status == "failed" for result in (*solution_results, *helpers_results)
    )
    summary = {
        "schema_version": 1,
        "status": "completed_with_errors" if failed else "completed",
        "group_key": context.profile.group_key,
        "content_rule_key": context.profile.content_rule_key,
        "targets": len(inventory.targets),
        "prepared": sum(result.status != "failed" for result in solution_results),
        "failed_stage_results": failed,
        "apply": context.apply,
        "targeted": context.targeted,
    }
    (context.run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
            else (active.output_root / f"{timestamp}-group-{profile.group_key}").resolve()
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
            discovery_label = "TARGET SELECTION" if targeted else (
                "LOCAL INVENTORY" if args.inventory_db else "INVENTORY"
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
                    apply_solution_scope=not targeted,
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
            if profile.workflow_kind == "content_rule":
                _run_content_rule_stages(
                    stage_context,
                    args,
                    full_inventory,
                    inventory,
                )
            else:
                prepared = _prepared_records(
                    active, args, gateway, profile, inventory, run_dir, reporter
                )
                _run_stages(stage_context, inventory, prepared)
        return 0
    finally:
        close = getattr(gateway, "close", None)
        if callable(close):
            close()


if __name__ == "__main__":
    raise SystemExit(main())
