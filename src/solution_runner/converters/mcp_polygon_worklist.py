"""Read and validate immutable worklists for resumed polygon jobs."""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import UUID

if __package__:
    from .mcp_polygon_client import _safe_exception
    from .mcp_polygon_config import PNG_CONTENT_TYPE
    from .mcp_polygon_models import (
        AssetCandidate,
        GroupInventory,
        GroupScope,
        PipelineError,
        ThemeScope,
    )
    from .mcp_polygon_util import _atomic_write_json, _sha256_bytes
else:
    from mcp_polygon_client import _safe_exception
    from mcp_polygon_config import PNG_CONTENT_TYPE
    from mcp_polygon_models import (
        AssetCandidate,
        GroupInventory,
        GroupScope,
        PipelineError,
        ThemeScope,
    )
    from mcp_polygon_util import _atomic_write_json, _sha256_bytes


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    """Read one required JSON object or fail with a bounded local error."""

    if not path.is_file():
        raise PipelineError(f"{label} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"{label} is invalid: {_safe_exception(exc)}") from exc
    if not isinstance(payload, dict):
        raise PipelineError(f"{label} must be a JSON object")
    return payload


def _read_run_events(run_dir: Path) -> list[dict[str, Any]]:
    """Read every structured event from one immutable source run."""

    path = run_dir / "events.jsonl"
    if not path.is_file():
        raise PipelineError(f"source events are missing: {path}")
    events: list[dict[str, Any]] = []
    try:
        for line_number, raw_line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not raw_line.strip():
                continue
            event = json.loads(raw_line)
            if not isinstance(event, dict):
                raise PipelineError(
                    f"source event line {line_number} is not a JSON object"
                )
            events.append(event)
    except json.JSONDecodeError as exc:
        raise PipelineError(
            f"source events contain invalid JSON: {_safe_exception(exc)}"
        ) from exc
    if not events:
        raise PipelineError("source events are empty")
    return events


def _validated_source_run_dir(source_run_dir: Path, run_dir: Path) -> Path:
    """Resolve a distinct existing source run directory."""

    source = source_run_dir.resolve()
    if not source.is_dir():
        raise PipelineError(f"resume source run does not exist: {source}")
    if source == run_dir:
        raise PipelineError("--resume-from-run must differ from --run-dir")
    return source


def _load_validated_worklist(
    *,
    source_run_dir: Path,
    run_dir: Path,
    catalog_snapshot_id: str,
    source_site_id: str,
    category_key: str,
    theme_titles: Sequence[str],
    scope: Sequence[tuple[ThemeScope, list[GroupScope]]],
) -> tuple[dict[str, GroupInventory], dict[str, Any]]:
    """Load and fail-closed validate one fixed-scope immutable worklist."""

    source = _validated_source_run_dir(source_run_dir, run_dir)
    payload = _read_json_object(source / "worklist.json", label="source worklist")
    if payload.get("schema_version") != 1:
        raise PipelineError("source worklist schema_version must be 1")
    expected_header = {
        "catalog_snapshot_id": catalog_snapshot_id,
        "source_site_id": source_site_id,
        "category_key": category_key,
        "theme_titles": list(theme_titles),
    }
    for field_name, expected_value in expected_header.items():
        if payload.get(field_name) != expected_value:
            raise PipelineError(
                f"source worklist {field_name} does not match the requested scope"
            )
    raw_targets = payload.get("targets")
    if not isinstance(raw_targets, list):
        raise PipelineError("source worklist targets must be a list")
    worklist_basis = json.dumps(
        raw_targets,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    worklist_sha256 = _sha256_bytes(worklist_basis)
    if payload.get("worklist_sha256") != worklist_sha256:
        raise PipelineError("source worklist SHA-256 does not match its targets")

    expected_groups = {
        group.source_group_id: (theme, group)
        for theme, groups in scope
        for group in groups
    }
    if int(payload.get("group_count") or -1) != len(expected_groups):
        raise PipelineError("source worklist group_count does not match fixed scope")
    candidate_fields = set(AssetCandidate.__dataclass_fields__)
    candidates_by_group: dict[str, list[AssetCandidate]] = {
        group_id: [] for group_id in expected_groups
    }
    seen_keys: set[str] = set()
    for position, raw_target in enumerate(raw_targets, start=1):
        if not isinstance(raw_target, dict) or set(raw_target) != candidate_fields:
            raise PipelineError(f"source worklist target {position} has invalid fields")
        string_fields = candidate_fields - {
            "theme_order_index",
            "group_order_index",
            "problem_order_index",
            "sections",
            "expected_vertices",
        }
        if any(
            not isinstance(raw_target.get(field_name), str)
            or not str(raw_target[field_name]).strip()
            for field_name in string_fields
        ):
            raise PipelineError(
                f"source worklist target {position} has invalid strings"
            )
        for field_name in (
            "theme_order_index",
            "group_order_index",
            "problem_order_index",
            "expected_vertices",
        ):
            if not isinstance(raw_target.get(field_name), int) or isinstance(
                raw_target.get(field_name), bool
            ):
                raise PipelineError(
                    f"source worklist target {position} has invalid {field_name}"
                )
        sections = raw_target.get("sections")
        if (
            not isinstance(sections, list)
            or not sections
            or any(section not in {"condition", "solution"} for section in sections)
        ):
            raise PipelineError(
                f"source worklist target {position} has invalid sections"
            )
        candidate_payload = dict(raw_target)
        candidate_payload["sections"] = tuple(sections)
        candidate = AssetCandidate(**candidate_payload)
        try:
            UUID(candidate.problem_id)
        except ValueError as exc:
            raise PipelineError(
                f"source worklist target {position} has invalid problem_id"
            ) from exc
        expected = expected_groups.get(candidate.source_group_id)
        if expected is None:
            raise PipelineError(
                f"source worklist target {position} escaped fixed source groups"
            )
        theme, group = expected
        exact_scope = (
            candidate.theme_title == theme.title
            and candidate.snapshot_theme_id == theme.snapshot_theme_id
            and candidate.theme_order_index == theme.order_index
            and candidate.group_key == group.group_key
            and candidate.group_order_index == group.order_index
            and candidate.expected_vertices == theme.expected_vertices
        )
        if not exact_scope:
            raise PipelineError(
                f"source worklist target {position} does not match fixed group metadata"
            )
        if candidate.stable_key in seen_keys:
            raise PipelineError(
                f"source worklist contains duplicate target {candidate.stable_key}"
            )
        seen_keys.add(candidate.stable_key)
        candidates_by_group[candidate.source_group_id].append(candidate)

    if int(payload.get("target_count") or -1) != len(seen_keys):
        raise PipelineError("source worklist target_count does not match targets")
    problem_count = len(
        {
            candidate.problem_id
            for candidates in candidates_by_group.values()
            for candidate in candidates
        }
    )
    if int(payload.get("problem_count") or -1) != problem_count:
        raise PipelineError("source worklist problem_count does not match targets")

    inventory_by_group: dict[str, GroupInventory] = {}
    for source_group_id, (theme, group) in expected_groups.items():
        candidates = candidates_by_group[source_group_id]
        problem_ids = list(
            dict.fromkeys(candidate.problem_id for candidate in candidates)
        )
        source_problem_ids = list(
            dict.fromkeys(candidate.source_problem_id for candidate in candidates)
        )
        inventory_by_group[source_group_id] = GroupInventory(
            theme_title=theme.title,
            snapshot_theme_id=theme.snapshot_theme_id,
            source_group_id=source_group_id,
            group_key=group.group_key,
            group_order_index=group.order_index,
            counts={
                "png_tasks": len(problem_ids),
                "png_assets": len(candidates),
                "ordinary_non_svg_assets": len(candidates),
            },
            non_svg_content_types={PNG_CONTENT_TYPE: len(candidates)},
            png_problem_ids=problem_ids,
            png_source_problem_ids=source_problem_ids,
            candidates=candidates,
        )
    _atomic_write_json(run_dir / "worklist.json", payload)
    return inventory_by_group, payload


def _event_candidate_key(
    event: dict[str, Any],
    *,
    candidates_by_key: dict[str, AssetCandidate],
    candidates_by_source_key: dict[tuple[str, str], list[AssetCandidate]],
) -> str | None:
    """Resolve one historical event to an exact immutable worklist target."""

    problem_id = str(event.get("problem_id") or "")
    asset_key = str(event.get("asset_key") or "")
    if problem_id and asset_key:
        key = f"{problem_id}:{asset_key}"
        return key if key in candidates_by_key else None
    source_problem_id = str(event.get("source_problem_id") or "")
    matches = candidates_by_source_key.get((source_problem_id, asset_key), [])
    event_group_key = str(event.get("group_key") or "")
    event_theme = str(event.get("theme") or "")
    if event_group_key:
        matches = [
            candidate for candidate in matches if candidate.group_key == event_group_key
        ]
    if event_theme:
        matches = [
            candidate for candidate in matches if candidate.theme_title == event_theme
        ]
    return matches[0].stable_key if len(matches) == 1 else None
