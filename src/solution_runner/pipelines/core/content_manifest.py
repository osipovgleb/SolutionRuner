"""Freeze and validate content-rule manifests for later application."""

from __future__ import annotations

import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .content_context import (
    _children,
    _condition_asset_id,
    _problem_identity,
    _resolved_group,
    _solution_assets,
    _solution_html,
)
from .content_gateway import RightTriangleGateway
from .errors import ContentPlanError as RightTrianglePlanError
from .models import GroupProfile, ProblemTarget


def _content_rule_manifest(
    gateway: RightTriangleGateway,
    targets: tuple[ProblemTarget, ...],
    *,
    profile: GroupProfile,
    parent_asset_id: str | None,
    parent_solution_assets: tuple[dict[str, str], ...],
    parent_solution_html: str = "",
    max_workers: int,
    on_record_prepared: Callable[[dict[str, Any], int], None] | None = None,
    record_factory: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Freeze exact per-task repairs for one already inventoried source group."""

    children = tuple(
        {
            "problem_id": target.problem_id,
            "source_problem_id": target.source_problem_id,
        }
        for target in targets
    )
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        records: list[dict[str, Any]] = []
        for index, record in enumerate(
            executor.map(
                lambda child: record_factory(
                    gateway,
                    child,
                    parent_asset_id,
                    profile.content_rule_key,
                    parent_solution_assets,
                    parent_solution_html,
                    profile.existing_solution_policy == "preserve",
                ),
                children,
            ),
            start=1,
        ):
            records.append(record)
            if on_record_prepared:
                on_record_prepared(record, index)
    return {
        "schema_version": 1,
        "kind": "right_triangle_sine_solution_repair",
        "prepared_at": datetime.now(UTC).isoformat(),
        "catalog_snapshot_id": profile.catalog_snapshot_id,
        "source_group_id": profile.source_group_id,
        "group_key": profile.group_key,
        "source_group_number": profile.group_key,
        "content_rule_key": profile.content_rule_key,
        "condition_asset": {
            "source_asset_id": parent_asset_id,
            "transformation_target_id": "asset:image_1",
        },
        "solution_assets": list(parent_solution_assets),
        "parent_solution_html": parent_solution_html,
        "records": records,
    }


def _read_content_rule_manifest(
    path: Path,
    targets: tuple[ProblemTarget, ...],
    profile: GroupProfile,
    *,
    requires_parent: Callable[[str], bool],
) -> dict[str, Any]:
    """Read and validate one frozen content-rule scope before resume."""

    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RightTrianglePlanError(
            "prepared content-rule manifest is unreadable"
        ) from exc
    records = manifest.get("records") if isinstance(manifest, dict) else None
    if (
        not isinstance(records, list)
        or manifest.get("schema_version") != 1
        or manifest.get("catalog_snapshot_id") != profile.catalog_snapshot_id
        or manifest.get("source_group_id") != profile.source_group_id
        or manifest.get("group_key") != profile.group_key
        or manifest.get("content_rule_key") != profile.content_rule_key
        or (
            not requires_parent(profile.content_rule_key)
            and (manifest.get("condition_asset") or {}).get("source_asset_id")
            not in (None, "")
        )
        or (
            profile.condition_asset_id is not None
            and (manifest.get("condition_asset") or {}).get("source_asset_id")
            != profile.condition_asset_id
        )
        or [record.get("problem_id") for record in records]
        != [target.problem_id for target in targets]
    ):
        raise RightTrianglePlanError("prepared content-rule manifest scope drifted")
    return manifest


def prepare_manifest(
    gateway: RightTriangleGateway,
    *,
    catalog_snapshot_id: str,
    source_group_number: str,
    max_workers: int,
    record_factory: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Discover one group and freeze every current deterministic repair."""

    if not 1 <= max_workers <= 10:
        raise RightTrianglePlanError("max_workers must be between 1 and 10")
    source_group_id = _resolved_group(
        gateway.find_source_catalog_path(
            catalog_snapshot_id,
            source_group_number,
            "group",
        )
    )
    children = _children(gateway.get_source_catalog_children(source_group_id, "group"))
    identities = [_problem_identity(child) for child in children]
    if not identities:
        raise RightTrianglePlanError("selected source group has no problems")
    asset_source_problem_id, asset_source_source_problem_id = identities[0]
    asset_source_context = gateway.get_problem_context(asset_source_problem_id)
    parent_asset_id = _condition_asset_id(asset_source_context)
    parent_solution_assets = _solution_assets(asset_source_context)
    parent_solution_html = _solution_html(asset_source_context)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        records = list(
            executor.map(
                lambda child: record_factory(
                    gateway,
                    child,
                    parent_asset_id,
                    parent_solution_assets=parent_solution_assets,
                    parent_solution_html=parent_solution_html,
                ),
                children,
            )
        )
    return {
        "schema_version": 1,
        "kind": "right_triangle_sine_solution_repair",
        "prepared_at": datetime.now(UTC).isoformat(),
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_group_id": source_group_id,
        "group_key": source_group_number,
        "source_group_number": source_group_number,
        "condition_asset": {
            "source_asset_id": parent_asset_id,
            "source_problem_id": asset_source_source_problem_id,
            "transformation_target_id": "asset:image_1",
        },
        "solution_assets": list(parent_solution_assets),
        "parent_solution_html": parent_solution_html,
        "records": records,
    }
