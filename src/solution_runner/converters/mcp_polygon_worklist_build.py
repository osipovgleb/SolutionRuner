"""Create immutable ordered worklists for polygon asset runs."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__:
    from .mcp_polygon_client import McpClient
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_inventory import build_group_inventory
    from .mcp_polygon_models import (
        GroupInventory,
        GroupScope,
        PipelineError,
        ThemeScope,
    )
    from .mcp_polygon_util import _atomic_write_json, _new_totals, _sha256_bytes
else:
    from mcp_polygon_client import McpClient
    from mcp_polygon_events import EventLogger
    from mcp_polygon_inventory import build_group_inventory
    from mcp_polygon_models import (
        AssetCandidate,
        GroupInventory,
        GroupScope,
        PipelineError,
        ThemeScope,
    )
    from mcp_polygon_util import _atomic_write_json, _new_totals, _sha256_bytes


def build_run_worklist(
    client: McpClient,
    *,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    category_title: str,
    theme_titles: Sequence[str],
    mode: str,
    converter_fingerprint: str,
    template_fingerprint: str,
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    run_dir: Path,
    logger: EventLogger,
) -> tuple[dict[str, GroupInventory], Counter[str]]:
    """Resolve every target once and persist the immutable ordered run worklist."""

    manifest: dict[str, Any] = {
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_site_id": source_site_id,
        "category_key": category_key,
        "category_title": category_title,
        "theme_titles": list(theme_titles),
        "mode": mode,
        "converter_sha256": converter_fingerprint,
        "template_sha256": template_fingerprint,
        "groups": [],
    }
    inventory_by_group: dict[str, GroupInventory] = {}
    ordered_candidates: list[AssetCandidate] = []
    totals = _new_totals()
    seen_candidate_keys: set[str] = set()
    manifest_path = run_dir / "inventory.json"

    total_group_count = sum(len(groups) for _, groups in scope)
    logger.emit(
        "worklist_build_start",
        themes=len(scope),
        groups=total_group_count,
    )
    group_position = 0
    for theme, groups in scope:
        for group in groups:
            group_position += 1
            logger.emit(
                "worklist_group_scan_start",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
                position=group_position,
                total_groups=total_group_count,
            )
            inventory = build_group_inventory(
                client,
                catalog_snapshot_id=catalog_snapshot_id,
                theme=theme,
                group=group,
            )
            if group.source_group_id in inventory_by_group:
                raise PipelineError(f"duplicate worklist group {group.source_group_id}")
            inventory_by_group[group.source_group_id] = inventory
            manifest["groups"].append(inventory.manifest_payload())
            _atomic_write_json(manifest_path, manifest)
            totals["groups"] += 1
            totals["inventory_png_tasks"] += inventory.counts.get("png_tasks", 0)
            totals["inventory_png_assets"] += inventory.counts.get("png_assets", 0)
            totals["inventory_non_svg_assets"] += inventory.counts.get(
                "ordinary_non_svg_assets", 0
            )
            for candidate in inventory.candidates:
                if candidate.stable_key in seen_candidate_keys:
                    raise PipelineError(
                        f"duplicate worklist candidate {candidate.stable_key}"
                    )
                seen_candidate_keys.add(candidate.stable_key)
                ordered_candidates.append(candidate)
            logger.emit(
                "worklist_group_scanned",
                theme=theme.title,
                group_key=group.group_key,
                source_group_id=group.source_group_id,
                position=group_position,
                total_groups=total_group_count,
                tasks=inventory.counts.get("png_tasks", 0),
                assets=inventory.counts.get("png_assets", 0),
            )

    target_payloads = [asdict(candidate) for candidate in ordered_candidates]
    worklist_basis = json.dumps(
        target_payloads,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    worklist_payload = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_site_id": source_site_id,
        "category_key": category_key,
        "theme_titles": list(theme_titles),
        "converter_sha256": converter_fingerprint,
        "template_sha256": template_fingerprint,
        "group_count": len(inventory_by_group),
        "problem_count": len(
            {candidate.problem_id for candidate in ordered_candidates}
        ),
        "target_count": len(ordered_candidates),
        "worklist_sha256": _sha256_bytes(worklist_basis),
        "targets": target_payloads,
    }
    _atomic_write_json(run_dir / "worklist.json", worklist_payload)
    logger.emit(
        "worklist_ready",
        groups=worklist_payload["group_count"],
        tasks=worklist_payload["problem_count"],
        assets=worklist_payload["target_count"],
        worklist_sha256=worklist_payload["worklist_sha256"],
    )
    return inventory_by_group, totals
