"""Validate dashboard targets before committing changes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .apply_results import SUCCESS


def verified_row(
    profiles: Mapping[str, Any], inventory: Any, group_key: str, problem_id: str
) -> dict[str, object]:
    if group_key not in profiles:
        raise KeyError(group_key)
    row = next(
        (
            item
            for item in inventory.list_items(group_key)
            if str(item["problem_id"]) == problem_id
        ),
        None,
    )
    if row is None:
        raise ValueError("problem does not belong to the initialized group")
    if row.get("dry_run_status") != "ready" and not row.get("error"):
        raise ValueError("problem requires a successful dry-run before apply")
    return row


def verified_group(
    profiles: Mapping[str, Any], inventory: Any, store: Any, group_key: str
) -> list[dict[str, object]]:
    if group_key not in profiles:
        raise KeyError(group_key)
    rows = inventory.list_items(group_key)
    if not rows:
        raise ValueError("initialized group has no tasks")
    group = store.get_group(group_key) if store is not None else None
    if not group or group.get("full_dry_run_status") != "ready":
        raise ValueError("group requires a successful full-group dry-run before apply")
    return rows


def helper_targets(
    inventory: Any, group_key: str, problem_id: str | None
) -> tuple[str, ...]:
    rows = inventory.list_items(group_key)
    if problem_id:
        rows = [row for row in rows if str(row["problem_id"]) == problem_id]
        if not rows:
            raise ValueError("problem does not belong to the initialized group")
    rows = [
        row
        for row in rows
        if row.get("helpers_status") not in SUCCESS
        and (row.get("has_solution") or row.get("apply_status") in SUCCESS)
    ]
    if not rows:
        raise ValueError("no tasks require Helpers")
    return tuple(str(row["problem_id"]) for row in rows)
