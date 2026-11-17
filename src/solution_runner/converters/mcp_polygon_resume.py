"""Restore polygon asset inventories for retries and guarded rollbacks."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

if __package__:
    from .mcp_polygon_config import PNG_CONTENT_TYPE
    from .mcp_polygon_events import EventLogger
    from .mcp_polygon_models import (
        AssetCandidate,
        GroupInventory,
        GroupScope,
        PipelineError,
        RollbackCandidate,
        ThemeScope,
    )
    from .mcp_polygon_util import _atomic_write_json, _new_totals
    from .mcp_polygon_worklist import (
        _event_candidate_key,
        _load_validated_worklist,
        _read_run_events,
        _validated_source_run_dir,
    )
else:
    from mcp_polygon_config import PNG_CONTENT_TYPE
    from mcp_polygon_events import EventLogger
    from mcp_polygon_models import (
        AssetCandidate,
        GroupInventory,
        GroupScope,
        PipelineError,
        RollbackCandidate,
        ThemeScope,
    )
    from mcp_polygon_util import _atomic_write_json, _new_totals
    from mcp_polygon_worklist import (
        _event_candidate_key,
        _load_validated_worklist,
        _read_run_events,
        _validated_source_run_dir,
    )


def _terminal_outcomes(events, candidates_by_key, candidates_by_source_key):
    terminal_by_key: dict[str, str] = {}
    for event in events:
        event_name = str(event.get("event") or "")
        key = _event_candidate_key(
            event,
            candidates_by_key=candidates_by_key,
            candidates_by_source_key=candidates_by_source_key,
        )
        if key is None:
            continue
        terminal = {
            "asset_replaced": "applied",
            "asset_rejected": "rejected",
            "asset_stale": "stale",
        }.get(event_name)
        if terminal is not None:
            terminal_by_key[key] = terminal
        elif event_name == "asset_error":
            reason = str(event.get("reason") or "")
            missing_source = (
                event.get("stage") == "prepare"
                and "/problem-assets/" in reason
                and ("404 Not Found" in reason or "410 Gone" in reason)
            )
            terminal_by_key[key] = "missing_source" if missing_source else "error"

    return terminal_by_key


def _filter_resumed_inventory(inventory_by_group, skip_reason_by_key):
    for inventory in inventory_by_group.values():
        original_candidates = inventory.candidates
        inventory.candidates = [
            candidate
            for candidate in original_candidates
            if candidate.stable_key not in skip_reason_by_key
        ]
        inventory.counts["resume_original_png_tasks"] = inventory.counts["png_tasks"]
        inventory.counts["resume_original_png_assets"] = inventory.counts["png_assets"]
        inventory.png_problem_ids = list(
            dict.fromkeys(candidate.problem_id for candidate in inventory.candidates)
        )
        inventory.png_source_problem_ids = list(
            dict.fromkeys(
                candidate.source_problem_id for candidate in inventory.candidates
            )
        )
        inventory.counts["png_tasks"] = len(inventory.png_problem_ids)
        inventory.counts["png_assets"] = len(inventory.candidates)
        inventory.counts["ordinary_non_svg_assets"] = len(inventory.candidates)
        inventory.non_svg_content_types = {PNG_CONTENT_TYPE: len(inventory.candidates)}


def _resume_inventory_from_run(
    *,
    source_run_dir: Path,
    run_dir: Path,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    theme_titles: Sequence[str],
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    converter_fingerprint: str,
    template_fingerprint: str,
    preserve_applied: bool = False,
    logger: EventLogger,
) -> tuple[dict[str, GroupInventory], Counter[str]]:
    """Filter a validated worklist using terminal outcomes from a prior run."""

    source = _validated_source_run_dir(source_run_dir, run_dir)
    inventory_by_group, worklist = _load_validated_worklist(
        source_run_dir=source,
        run_dir=run_dir,
        catalog_snapshot_id=catalog_snapshot_id,
        source_site_id=source_site_id,
        category_key=category_key,
        theme_titles=theme_titles,
        scope=scope,
    )
    events = _read_run_events(source)
    run_starts = [event for event in events if event.get("event") == "run_start"]
    if len(run_starts) != 1:
        raise PipelineError("source run must contain exactly one run_start event")
    source_start = run_starts[0]
    source_converter = str(
        worklist.get("converter_sha256") or source_start.get("converter_sha256") or ""
    )
    source_template = str(
        worklist.get("template_sha256") or source_start.get("template_sha256") or ""
    )
    if not source_converter or not source_template:
        raise PipelineError("source run has no converter/template fingerprints")
    same_renderer = (
        source_converter == converter_fingerprint
        and source_template == template_fingerprint
    )
    all_candidates = [
        candidate
        for inventory in inventory_by_group.values()
        for candidate in inventory.candidates
    ]
    candidates_by_key = {
        candidate.stable_key: candidate for candidate in all_candidates
    }
    candidates_by_source_key: dict[tuple[str, str], list[AssetCandidate]] = {}
    for candidate in all_candidates:
        candidates_by_source_key.setdefault(
            (candidate.source_problem_id, candidate.asset_key), []
        ).append(candidate)

    terminal_by_key = _terminal_outcomes(
        events, candidates_by_key, candidates_by_source_key
    )

    skip_reason_by_key: dict[str, str] = {}
    for key, terminal in terminal_by_key.items():
        should_skip = (
            terminal in {"missing_source", "stale"}
            or (terminal == "applied" and (same_renderer or preserve_applied))
            or (terminal == "rejected" and same_renderer)
        )
        if should_skip:
            skip_reason_by_key[key] = terminal

    totals = _new_totals()
    totals["groups"] = len(inventory_by_group)
    totals["inventory_png_tasks"] = int(worklist["problem_count"])
    totals["inventory_png_assets"] = int(worklist["target_count"])
    totals["inventory_non_svg_assets"] = int(worklist["target_count"])
    _filter_resumed_inventory(inventory_by_group, skip_reason_by_key)

    reason_counts = Counter(skip_reason_by_key.values())
    remaining_candidates = [
        candidate
        for inventory in inventory_by_group.values()
        for candidate in inventory.candidates
    ]
    remaining_problem_count = len(
        {candidate.problem_id for candidate in remaining_candidates}
    )
    totals["resume_skipped_applied"] = reason_counts["applied"]
    totals["resume_skipped_rejected_same_renderer"] = reason_counts["rejected"]
    totals["resume_skipped_missing_source"] = reason_counts["missing_source"]
    totals["resume_skipped_stale"] = reason_counts["stale"]
    totals["resume_remaining_assets"] = len(remaining_candidates)
    totals["resume_remaining_tasks"] = remaining_problem_count
    resume_payload = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_run_dir": str(source),
        "source_worklist_sha256": worklist["worklist_sha256"],
        "source_converter_sha256": source_converter,
        "source_template_sha256": source_template,
        "current_converter_sha256": converter_fingerprint,
        "current_template_sha256": template_fingerprint,
        "same_renderer": same_renderer,
        "preserve_applied": preserve_applied,
        "remaining_task_count": remaining_problem_count,
        "remaining_target_count": len(remaining_candidates),
        "skip_counts": dict(sorted(reason_counts.items())),
    }
    _atomic_write_json(run_dir / "resume.json", resume_payload)
    logger.emit(
        "resume_ready",
        source_run_dir=str(source),
        same_renderer=same_renderer,
        preserve_applied=preserve_applied,
        tasks=remaining_problem_count,
        assets=len(remaining_candidates),
        applied=reason_counts["applied"],
        rejected=reason_counts["rejected"],
        missing=reason_counts["missing_source"],
        stale=reason_counts["stale"],
    )
    return inventory_by_group, totals


def _rollback_inventory_from_run(
    *,
    source_run_dir: Path,
    run_dir: Path,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    theme_titles: Sequence[str],
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
    logger: EventLogger,
) -> tuple[dict[str, list[RollbackCandidate]], Counter[str]]:
    """Build an exact guarded rollback list from successful source-run events."""

    source = _validated_source_run_dir(source_run_dir, run_dir)
    inventory_by_group, worklist = _load_validated_worklist(
        source_run_dir=source,
        run_dir=run_dir,
        catalog_snapshot_id=catalog_snapshot_id,
        source_site_id=source_site_id,
        category_key=category_key,
        theme_titles=theme_titles,
        scope=scope,
    )
    all_candidates = [
        candidate
        for inventory in inventory_by_group.values()
        for candidate in inventory.candidates
    ]
    candidates_by_key = {
        candidate.stable_key: candidate for candidate in all_candidates
    }
    candidates_by_source_key: dict[tuple[str, str], list[AssetCandidate]] = {}
    for candidate in all_candidates:
        candidates_by_source_key.setdefault(
            (candidate.source_problem_id, candidate.asset_key), []
        ).append(candidate)
    applied_by_key: dict[str, RollbackCandidate] = {}
    for event in _read_run_events(source):
        if event.get("event") != "asset_replaced":
            continue
        key = _event_candidate_key(
            event,
            candidates_by_key=candidates_by_key,
            candidates_by_source_key=candidates_by_source_key,
        )
        if key is None:
            raise PipelineError("asset_replaced event does not map to the worklist")
        candidate = candidates_by_key[key]
        if (
            str(event.get("theme") or "") != candidate.theme_title
            or str(event.get("group_key") or "") != candidate.group_key
            or str(event.get("source_problem_id") or "") != candidate.source_problem_id
        ):
            raise PipelineError("asset_replaced event escaped its worklist metadata")
        transformation_target_id = str(event.get("transformation_target_id") or "")
        source_asset_id = str(event.get("source_asset_id") or "")
        output_sha256 = str(event.get("output_sha256") or "").lower()
        if not transformation_target_id.startswith("asset:"):
            raise PipelineError(
                "asset_replaced event has invalid transformation target"
            )
        try:
            UUID(source_asset_id)
        except ValueError as exc:
            raise PipelineError(
                "asset_replaced event has invalid source_asset_id"
            ) from exc
        if len(output_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in output_sha256
        ):
            raise PipelineError("asset_replaced event has invalid output SHA-256")
        applied_by_key[key] = RollbackCandidate(
            candidate=candidate,
            transformation_target_id=transformation_target_id,
            source_asset_id=source_asset_id,
            output_sha256=output_sha256,
        )

    rollback_by_group: dict[str, list[RollbackCandidate]] = {
        source_group_id: [] for source_group_id in inventory_by_group
    }
    for candidate in all_candidates:
        rollback_candidate = applied_by_key.get(candidate.stable_key)
        if rollback_candidate is not None:
            rollback_by_group[candidate.source_group_id].append(rollback_candidate)
    rollback_targets = [
        {
            **asdict(item.candidate),
            "transformation_target_id": item.transformation_target_id,
            "source_asset_id": item.source_asset_id,
            "output_sha256": item.output_sha256,
        }
        for source_group_id in rollback_by_group
        for item in rollback_by_group[source_group_id]
    ]
    rollback_payload = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_run_dir": str(source),
        "source_worklist_sha256": worklist["worklist_sha256"],
        "target_count": len(rollback_targets),
        "targets": rollback_targets,
    }
    _atomic_write_json(run_dir / "rollback.json", rollback_payload)
    totals = _new_totals()
    totals["groups"] = len(rollback_by_group)
    totals["rollback_targets"] = len(rollback_targets)
    logger.emit(
        "rollback_ready",
        source_run_dir=str(source),
        groups=len(rollback_by_group),
        tasks=len({item["problem_id"] for item in rollback_targets}),
        assets=len(rollback_targets),
    )
    return rollback_by_group, totals
