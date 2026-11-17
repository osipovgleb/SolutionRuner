"""Collect per-problem metadata for a local dashboard inventory."""

from typing import Any

from solution_runner.group_inventory_store import (
    GroupInventoryAsset,
    GroupInventoryItem,
)


def build_inventory_rows(
    gateway,
    identities,
    contexts,
    context_errors,
    rejected_problem_ids,
    group_image_types,
):
    from .initialization import (
        GroupInitializationError,
        _content_type,
        _section_key,
        _sections,
    )

    metadata_by_id: dict[str, dict[str, Any]] = {}
    inventory_items: list[GroupInventoryItem] = []
    inventory_assets: list[GroupInventoryAsset] = []

    for position, (problem_id, source_problem_id) in enumerate(identities):
        if problem_id in rejected_problem_ids:
            continue
        content = contexts.get(problem_id, {})
        sections = _sections(content)
        section_keys = {_section_key(section) for section in sections}
        asset_sections = {
            str(asset_key): _section_key(section)
            for section in sections
            for asset_key in section.get("asset_keys", [])
        }
        inventory_items.append(
            GroupInventoryItem(
                problem_id=problem_id,
                source_problem_id=source_problem_id,
                position=position,
                has_condition="condition" in section_keys,
                has_solution="solution" in section_keys,
                has_answer="answer" in section_keys,
                content_status=(
                    "unavailable" if problem_id in context_errors else "available"
                ),
                inventory_error=context_errors.get(problem_id),
            )
        )
        assets = content.get("assets", [])
        if not isinstance(assets, list):
            raise GroupInitializationError(
                f"task {source_problem_id} has an invalid asset list"
            )
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            asset_id = str(asset.get("asset_id") or "").strip()
            asset_key = str(asset.get("asset_key") or "").strip()
            section_key = asset_sections.get(asset_key, "")
            if not asset_id or not asset_key or not section_key:
                continue
            content_type = group_image_types.get(
                (source_problem_id, section_key, asset_key, asset_id), ""
            )
            if not content_type and asset_id not in metadata_by_id:
                metadata = gateway.get_asset_metadata(asset_id)
                metadata_by_id[asset_id] = (
                    metadata if isinstance(metadata, dict) else {}
                )
            inventory_assets.append(
                GroupInventoryAsset(
                    problem_id=problem_id,
                    asset_id=asset_id,
                    asset_key=asset_key,
                    section_key=section_key,
                    content_type=content_type
                    or _content_type(metadata_by_id[asset_id]),
                )
            )

    return inventory_items, inventory_assets
