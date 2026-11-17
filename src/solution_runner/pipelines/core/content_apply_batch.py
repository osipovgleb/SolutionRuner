"""Apply frozen content records in bounded, checkpointed batches."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any

from .content_gateway import RightTriangleGateway
from .content_reporting import _summary, _write_checkpoint
from .errors import ContentPlanError as RightTrianglePlanError


def apply_frozen_manifest(
    gateway: RightTriangleGateway,
    manifest: dict[str, Any],
    *,
    batch_size: int,
    max_workers: int,
    checkpoint_path: Path,
    batch_pause_seconds: float = 0.0,
    on_batch_complete: Callable[[list[dict[str, Any]], int], None] | None = None,
    services: Any,
) -> dict[str, Any]:
    """Apply frozen records in bounded batches with restartable readback."""

    if batch_size <= 0:
        raise RightTrianglePlanError("batch_size must be positive")
    if batch_pause_seconds < 0:
        raise RightTrianglePlanError("batch_pause_seconds cannot be negative")
    if not 1 <= max_workers <= 10:
        raise RightTrianglePlanError("max_workers must be between 1 and 10")
    records = manifest.get("records")
    content_rule_key = manifest.get("content_rule_key")
    if content_rule_key is not None and not isinstance(content_rule_key, str):
        raise RightTrianglePlanError("prepared manifest content rule is invalid")
    services._planner_constraints(content_rule_key)
    raw_solution_assets = manifest.get("solution_assets", [])
    if not isinstance(raw_solution_assets, list) or not all(
        isinstance(item, dict) for item in raw_solution_assets
    ):
        raise RightTrianglePlanError("manifest solution assets are invalid")
    parent_solution_assets = tuple(deepcopy(item) for item in raw_solution_assets)
    parent_solution_html = str(manifest.get("parent_solution_html") or "")
    parent_asset_id = str(
        (manifest.get("condition_asset") or {}).get("source_asset_id") or ""
    )
    if not isinstance(records, list) or (
        not parent_asset_id
        and services._requires_parent_condition_asset(content_rule_key)
    ):
        raise RightTrianglePlanError("prepared manifest is incomplete")
    services._registered_handler(content_rule_key).validate_manifest(gateway, manifest)
    results: list[dict[str, Any]] = []
    for offset in range(0, len(records), batch_size):
        batch = records[offset : offset + batch_size]
        with ThreadPoolExecutor(
            max_workers=min(max_workers, len(batch) or 1)
        ) as executor:
            batch_results = list(
                executor.map(
                    lambda record: services._apply_record(
                        gateway,
                        record,
                        parent_asset_id,
                        content_rule_key,
                        parent_solution_assets,
                        parent_solution_html,
                    ),
                    batch,
                )
            )
        results.extend(batch_results)
        _write_checkpoint(checkpoint_path, _summary(results))
        if on_batch_complete:
            on_batch_complete(batch_results, len(results))
        if offset + batch_size < len(records) and batch_pause_seconds:
            time.sleep(batch_pause_seconds)
    return _summary(results)
