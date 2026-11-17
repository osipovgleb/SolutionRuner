"""Reconcile registered groups with their latest local runs."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .store_common import _now, _source_label, _system_column
from .store_runs import discover_latest_runs

if TYPE_CHECKING:
    from .store import DashboardStore


def sync_groups(
    store: DashboardStore,
    profiles: Mapping[str, Any],
    var_dir: Path,
    *,
    inventory_store: Any | None = None,
) -> dict[str, int]:
    runs, warnings = discover_latest_runs(var_dir)
    keys = set(profiles)
    store.prune_inactive_groups(keys)
    for group_key in keys:
        profile = profiles.get(group_key)
        run = runs.get(group_key, {})
        registered = profile is not None
        source_id = str(profile.catalog_snapshot_id) if profile else "history"
        total = int(run.get("total", 0))
        transformed = int(run.get("transformed", 0))
        helpers = int(run.get("helpers", 0))
        errors = int(run.get("errors", 0))
        blocked = int(run.get("blocked", 0))
        handler = None
        if profile is not None:
            handler = profile.content_rule_key or profile.strategy_key
        store.upsert_fact(
            {
                "group_key": group_key,
                "title": profile.theme_title if profile else f"Группа {group_key}",
                "path": profile.theme_title if profile else "История запусков",
                "source": _source_label(source_id) if profile else "История",
                "source_id": source_id,
                "registered": int(registered),
                "legacy": int(not registered),
                "workflow": profile.workflow_kind if profile else None,
                "handler": handler,
                "total": total,
                "transformed": transformed,
                "helpers": helpers,
                "errors": errors,
                "blocked": blocked,
                "latest_run": run.get("run_name"),
                "run_status": run.get("status"),
                "system_column": _system_column(
                    registered=registered,
                    has_run=bool(run),
                    total=total,
                    transformed=transformed,
                    helpers=helpers,
                    errors=errors,
                    blocked=blocked,
                ),
                "synced_at": _now(),
            }
        )
    if inventory_store is not None:
        for group_key in profiles:
            if inventory_store.get(group_key) is not None:
                store.reconcile_problem_counts(
                    group_key,
                    inventory_store.list_items(group_key),
                )
    return {"groups": len(keys), "runs": len(runs), "warnings": warnings}
