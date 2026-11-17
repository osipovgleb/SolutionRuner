"""Run solution and helper stages and persist their summaries."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..core.models import GroupProfile, PreparedFigure
from .helpers_runtime import verify_existing_solutions
from .inventory import GroupInventory
from .launcher_records import _write_results
from .progress import ProgressReporter
from .strategies import get_solution_strategy

if TYPE_CHECKING:
    from .launcher import LauncherDependencies


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


def _run_stages(
    context: _StageContext,
    inventory: GroupInventory,
    prepared: tuple[PreparedFigure, ...],
    *,
    helpers_from_existing_solution: bool = False,
    force_apply: bool = False,
) -> None:
    """Run solution and Helpers stages and persist their terminal summary."""

    if helpers_from_existing_solution:
        solution_results = verify_existing_solutions(
            context.gateway,
            inventory.targets,
            context.profile,
            context.reporter,
        )
    else:
        if context.profile.strategy_key is None:
            raise ValueError("geometry workflow requires strategy_key")
        strategy = get_solution_strategy(context.profile.strategy_key)
        solution_kwargs = {
            "apply": context.apply,
            "max_workers": context.max_workers,
        }
        if force_apply:
            solution_kwargs["force_apply"] = True
        solution_results = context.active.solution_stage(
            context.gateway,
            prepared,
            context.profile,
            strategy,
            context.reporter,
            **solution_kwargs,
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
        "prepared": sum(result.status != "skipped" for result in solution_results),
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
