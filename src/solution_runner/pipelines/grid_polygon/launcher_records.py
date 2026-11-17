"""Select frozen launcher targets and persist stage results."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..core.models import PreparedFigure, ProblemStageResult
from .inventory import GroupInventory
from .manifest import FrozenRunScope


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
        parser.error(
            f"--only-{field.replace('_', '-')} is outside the frozen group scope"
        )
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
