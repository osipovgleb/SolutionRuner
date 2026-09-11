"""Adapt the dashboard's local group index to the common launcher inventory."""

from __future__ import annotations

from typing import Any

from solution_runner.group_inventory_store import GroupInventoryStore

from ..grid_polygon.inventory import GroupInventory, RASTER_CONTENT_TYPES
from .models import ProblemTarget


def load_group_inventory(
    store: GroupInventoryStore,
    profile: Any,
    *,
    apply_solution_scope: bool = True,
) -> GroupInventory:
    """Load one initialized group without repeating MCP discovery."""

    snapshot = store.get(str(profile.group_key))
    if snapshot is None or snapshot.status != "ready":
        raise ValueError(f"group {profile.group_key} has no ready local inventory")
    if (
        snapshot.catalog_snapshot_id != str(profile.catalog_snapshot_id)
        or snapshot.source_group_id != str(profile.source_group_id)
    ):
        raise ValueError(f"group {profile.group_key} local inventory does not match its profile")

    assets_by_problem: dict[str, list[Any]] = {}
    for asset in snapshot.assets:
        assets_by_problem.setdefault(asset.problem_id, []).append(asset)

    targets: list[ProblemTarget] = []
    png: list[ProblemTarget] = []
    svg: list[ProblemTarget] = []
    for item in snapshot.items:
        if item.content_status != "available":
            continue
        assets = assets_by_problem.get(item.problem_id, [])
        generated_solution = any(
            asset.section_key == "solution"
            and asset.asset_key == "generated_solution_diagram"
            for asset in assets
        )
        scope = getattr(profile, "solution_scope", "all")
        if apply_solution_scope and scope == "missing_only" and item.has_solution:
            continue
        if apply_solution_scope and scope == "missing_or_pipeline_generated" and item.has_solution and not generated_solution:
            continue

        condition_asset = next(
            (
                asset
                for asset in assets
                if asset.section_key == "condition" and asset.asset_key == "image_1"
            ),
            None,
        )
        if profile.workflow_kind != "content_rule" and (
            condition_asset is None
            or condition_asset.content_type not in RASTER_CONTENT_TYPES | {"image/svg+xml"}
        ):
            continue
        target = ProblemTarget(
            problem_id=item.problem_id,
            source_problem_id=item.source_problem_id,
            source_group_id=snapshot.source_group_id,
            group_key=snapshot.group_key,
            problem_order_index=item.position,
        )
        targets.append(target)
        if profile.workflow_kind == "content_rule":
            continue
        if condition_asset.content_type in RASTER_CONTENT_TYPES:
            png.append(target)
        else:
            svg.append(target)

    return GroupInventory(tuple(targets), tuple(png), tuple(svg))
