"""Discover catalog scope and build inventories of convertible assets."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from typing import Any

if __package__:
    from . import mcp_polygon_image_index as image_index
    from .mcp_polygon_client import McpClient
    from .mcp_polygon_config import (
        DEFAULT_CATALOG_SNAPSHOT_ID,
        DEFAULT_CATEGORY_KEY,
        DEFAULT_CATEGORY_TITLE,
        DEFAULT_SOURCE_SITE_ID,
        EXPECTED_VERTICES_BY_THEME,
        FIXED_SOURCE_GROUPS,
        FIXED_THEME_CONFIG,
        RASTER_CONTENT_TYPES,
        SVG_CONTENT_TYPE,
    )
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_models import (
        AssetCandidate,
        GroupInventory,
        GroupScope,
        PipelineError,
        ThemeScope,
    )
else:
    import mcp_polygon_image_index as image_index
    from mcp_polygon_client import McpClient
    from mcp_polygon_config import (
        DEFAULT_CATALOG_SNAPSHOT_ID,
        DEFAULT_CATEGORY_KEY,
        DEFAULT_CATEGORY_TITLE,
        DEFAULT_SOURCE_SITE_ID,
        EXPECTED_VERTICES_BY_THEME,
        FIXED_SOURCE_GROUPS,
        FIXED_THEME_CONFIG,
        RASTER_CONTENT_TYPES,
        SVG_CONTENT_TYPE,
    )
    from mcp_polygon_events import EventLogger
    from mcp_polygon_models import (
        AssetCandidate,
        GroupInventory,
        GroupScope,
        PipelineError,
        ThemeScope,
    )


_normalized_content_type = image_index._normalized_content_type


def discover_catalog_scope(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    category_key: str,
    category_title: str,
    theme_titles: Sequence[str],
    group_keys: Sequence[str] | None = None,
    logger: EventLogger,
) -> tuple[str, list[tuple[ThemeScope, list[GroupScope]]]]:
    """Build the immutable production scope without reading the catalog tree."""

    del client
    if catalog_snapshot_id != DEFAULT_CATALOG_SNAPSHOT_ID:
        raise PipelineError("fixed theme UUIDs require the configured catalog snapshot")
    if category_key != DEFAULT_CATEGORY_KEY or category_title != DEFAULT_CATEGORY_TITLE:
        raise PipelineError("fixed theme UUIDs require the configured category")
    if len(set(theme_titles)) != len(theme_titles):
        raise PipelineError("target theme titles must be unique")

    requested_group_keys = set(group_keys or [])
    scope: list[tuple[ThemeScope, list[GroupScope]]] = []
    all_group_ids: set[str] = set()
    for requested_title in theme_titles:
        config = FIXED_THEME_CONFIG.get(requested_title)
        if config is None:
            raise PipelineError(
                f"no fixed UUID configuration for theme {requested_title!r}"
            )
        theme = ThemeScope(
            title=requested_title,
            snapshot_theme_id=str(config["snapshot_theme_id"]),
            source_theme_id=str(config["source_theme_id"]),
            order_index=int(config["order_index"]),
            source_groups_count=int(config["source_groups_count"]),
            expected_vertices=EXPECTED_VERTICES_BY_THEME[requested_title],
        )
        configured_groups = FIXED_SOURCE_GROUPS.get(requested_title)
        if configured_groups is None:
            raise PipelineError(f"no fixed source groups for theme {theme.title!r}")
        if len(configured_groups) != theme.source_groups_count:
            raise PipelineError(
                f"theme {theme.title!r} declares {theme.source_groups_count} groups "
                f"but fixes {len(configured_groups)}"
            )
        groups: list[GroupScope] = []
        seen_group_keys: set[str] = set()
        for order_index, (group_id, group_key) in enumerate(configured_groups):
            if not group_id or group_id in all_group_ids:
                raise PipelineError(
                    f"theme {theme.title!r} has a missing/duplicate group id"
                )
            if not group_key or group_key in seen_group_keys:
                raise PipelineError(
                    f"theme {theme.title!r} has a missing/duplicate group key"
                )
            all_group_ids.add(group_id)
            seen_group_keys.add(group_key)
            groups.append(
                GroupScope(
                    source_group_id=group_id,
                    group_key=group_key,
                    order_index=order_index,
                )
            )
        selected_groups = [
            group
            for group in groups
            if not requested_group_keys or group.group_key in requested_group_keys
        ]
        if not selected_groups:
            continue
        logger.emit(
            "theme_scope_loaded",
            theme=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            groups=len(selected_groups),
        )
        scope.append((theme, selected_groups))
    selected_group_keys = {
        group.group_key for _theme, groups in scope for group in groups
    }
    missing_group_keys = sorted(requested_group_keys - selected_group_keys)
    if missing_group_keys:
        raise PipelineError(
            f"group keys are outside the selected fixed themes: {missing_group_keys}"
        )
    return DEFAULT_SOURCE_SITE_ID, scope


def _load_group_targets(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    group: GroupScope,
    source_problem_ids: Sequence[str],
) -> dict[str, dict[str, Any]]:
    """Resolve current problem UUIDs and Normalized status for one exact group."""

    del catalog_snapshot_id
    ordered_source_problem_ids = list(
        dict.fromkeys(
            str(value).strip() for value in source_problem_ids if str(value).strip()
        )
    )
    targets_by_source_problem_id: dict[str, dict[str, Any]] = {}
    children = client.call(
        "get_source_catalog_children",
        {"parent_id": group.source_group_id, "parent_type": "group"},
    )
    children_by_source_problem_id: dict[str, tuple[int, str]] = {}
    for order_index, item in enumerate(children.get("items", [])):
        if not isinstance(item, dict):
            continue
        problem_id = str(item.get("uuid") or "")
        name = str(item.get("name") or "")
        prefix = "Задача "
        if not problem_id or not name.startswith(prefix):
            raise PipelineError("group child has no canonical problem UUID/source id")
        source_problem_id = name[len(prefix) :].strip()
        if not source_problem_id or source_problem_id in children_by_source_problem_id:
            raise PipelineError(
                "group children contain a missing/duplicate source problem id"
            )
        children_by_source_problem_id[source_problem_id] = (order_index, problem_id)

    for source_problem_id in ordered_source_problem_ids:
        child = children_by_source_problem_id.get(source_problem_id)
        if child is None:
            continue
        order_index, problem_id = child
        state = client.call("get_problem_pipeline_state", {"problem_id": problem_id})
        statuses = state.get("statuses")
        normalized_status = (
            str(statuses.get("normalized") or "") if isinstance(statuses, dict) else ""
        )
        targets_by_source_problem_id[source_problem_id] = {
            "source_group_id": group.source_group_id,
            "problem_id": problem_id,
            "source_problem_id": source_problem_id,
            "order_index": order_index,
            "source_group_status": "processing",
            "problem_source_content_status": normalized_status,
            "has_normalized_content": normalized_status in {"ready", "rejected"},
        }
    return targets_by_source_problem_id


_validate_image_scope = image_index._validate_image_scope


_index_section_images = image_index._index_section_images


def _collect_candidates(
    theme, group, targets, images_by_source_problem, source_ids, concrete_problem_count
):
    """Classify eligible image targets and build deterministic candidates."""
    counts: Counter[str] = Counter(total_group_items=concrete_problem_count)
    content_types: Counter[str] = Counter()
    candidates: list[AssetCandidate] = []
    png_problem_ids: set[str] = set()
    png_source_problem_ids: set[str] = set()
    for source_problem_id in source_ids:
        target = targets.get(source_problem_id)
        if target is None:
            counts["missing_parser_target"] += 1
            continue
        problem_id = str(target.get("problem_id") or "")
        counts["parser_targets"] += 1
        group_status = str(target.get("source_group_status") or "")
        problem_status = str(target.get("problem_source_content_status") or "")
        if group_status == "rejected":
            raise PipelineError(
                f"configured source group {group.source_group_id} is unexpectedly rejected"
            )
        if problem_status == "rejected":
            counts["rejected_problems"] += 1
            continue
        if target.get("has_normalized_content") is not True:
            counts["without_normalized_content"] += 1
            continue
        counts["eligible_problems"] += 1
        image_rows = images_by_source_problem.get(source_problem_id, {})
        for (asset_key, kind, content_type), sections in sorted(image_rows.items()):
            counts["all_section_images"] += 1
            if kind != "ordinary_image":
                counts["formula_or_unknown_images"] += 1
                continue
            counts["ordinary_images"] += 1
            if content_type == SVG_CONTENT_TYPE:
                counts["ordinary_svg_assets"] += 1
                continue
            counts["ordinary_non_svg_assets"] += 1
            content_types[content_type or "unknown"] += 1
            if content_type not in RASTER_CONTENT_TYPES:
                counts["ordinary_non_png_assets"] += 1
                continue
            counts["png_assets"] += 1
            png_problem_ids.add(problem_id)
            png_source_problem_ids.add(source_problem_id)
            candidates.append(
                AssetCandidate(
                    theme_title=theme.title,
                    snapshot_theme_id=theme.snapshot_theme_id,
                    theme_order_index=theme.order_index,
                    source_group_id=group.source_group_id,
                    group_key=group.group_key,
                    group_order_index=group.order_index,
                    problem_id=problem_id,
                    source_problem_id=source_problem_id,
                    problem_order_index=int(target.get("order_index") or 0),
                    asset_key=asset_key,
                    sections=tuple(sorted(sections)),
                    expected_vertices=theme.expected_vertices,
                )
            )
    return counts, content_types, candidates, png_problem_ids, png_source_problem_ids


def build_group_inventory(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    theme: ThemeScope,
    group: GroupScope,
) -> GroupInventory:
    """Select every current ordinary PNG from non-rejected normalized problems."""
    images_payload = client.call(
        "get_source_catalog_section_images",
        {"target_id": group.source_group_id, "target_type": "group"},
    )
    concrete_problem_count = _validate_image_scope(
        images_payload, catalog_snapshot_id, group
    )

    images_by_source_problem = _index_section_images(images_payload)

    ordinary_image_source_problem_ids = sorted(
        (
            source_problem_id
            for source_problem_id, image_rows in images_by_source_problem.items()
            if any(kind == "ordinary_image" for _, kind, _ in image_rows)
        ),
        key=lambda value: (len(value), value),
    )
    targets = _load_group_targets(
        client,
        catalog_snapshot_id=catalog_snapshot_id,
        group=group,
        source_problem_ids=ordinary_image_source_problem_ids,
    )

    counts, content_types, candidates, png_problem_ids, png_source_problem_ids = (
        _collect_candidates(
            theme,
            group,
            targets,
            images_by_source_problem,
            ordinary_image_source_problem_ids,
            concrete_problem_count,
        )
    )
    escaped_source_problem_ids = set(targets) - set(ordinary_image_source_problem_ids)
    if escaped_source_problem_ids:
        raise PipelineError(
            "parser targets escaped requested source problems: "
            f"{sorted(escaped_source_problem_ids)[:3]}"
        )
    candidates.sort(
        key=lambda item: (
            item.problem_order_index,
            item.source_problem_id,
            item.asset_key,
        )
    )
    counts["png_tasks"] = len(png_problem_ids)
    counts.setdefault("png_assets", 0)
    return GroupInventory(
        theme_title=theme.title,
        snapshot_theme_id=theme.snapshot_theme_id,
        source_group_id=group.source_group_id,
        group_key=group.group_key,
        group_order_index=group.order_index,
        counts=dict(sorted(counts.items())),
        non_svg_content_types=dict(sorted(content_types.items())),
        png_problem_ids=sorted(png_problem_ids),
        png_source_problem_ids=sorted(
            png_source_problem_ids,
            key=lambda value: (len(value), value),
        ),
        candidates=candidates,
    )
