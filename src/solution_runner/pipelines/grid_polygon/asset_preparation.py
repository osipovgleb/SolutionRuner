"""Freeze converter events and existing SVGs into reusable prepared polygons."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable, Protocol

from .geometry.grid_polygon import (
    ordered_coordinates_from_svg,
    parse_coordinate_alt,
    parse_grid_polygon,
    polygon_sha256,
    serialize_coordinate_alt,
)
from ..core.models import GroupProfile, PreparedGridPolygon, ProblemTarget


DEFAULT_IMAGE_RUNNER = (
    Path(__file__).resolve().parents[2]
    / "converters"
    / "mcp_grid_polygon_transformations.py"
)


class PreparedAssetError(RuntimeError):
    """Report incomplete, inconsistent, or drifting preparation evidence."""


@dataclass(frozen=True)
class ExistingSvgAsset:
    """Carry one downloaded existing condition SVG and its current metadata."""

    asset_id: str
    content_type: str
    alt_text: str
    svg_bytes: bytes


@dataclass(frozen=True)
class _PreparationContext:
    """Carry shared evidence required to freeze converter events."""

    run_dir: Path
    profile: GroupProfile
    run_start: dict[str, object]
    applied: bool


class ExistingSvgGateway(Protocol):
    """Define the narrow asset operations needed before MCP runtime extraction."""

    def download_existing_svg(self, target: ProblemTarget) -> ExistingSvgAsset:
        """Download one current condition SVG and return its metadata."""

    def replace_existing_svg_alt(
        self,
        target: ProblemTarget,
        asset: ExistingSvgAsset,
        alt_text: str,
    ) -> ExistingSvgAsset:
        """Persist canonical alt metadata and return authoritative readback."""


CommandExecutor = Callable[[tuple[str, ...]], int]


def build_image_runner_command(
    profile: GroupProfile,
    run_dir: Path,
    *,
    apply: bool,
    only_source_problem_id: str | None = None,
    python_executable: str = sys.executable,
    image_runner: Path = DEFAULT_IMAGE_RUNNER,
    batch_size: int = 10,
    batch_pause_seconds: float = 0.0,
    max_workers: int = 10,
) -> tuple[str, ...]:
    """Build one explicit-group converter command without shell interpolation."""

    if only_source_problem_id is not None:
        raise PreparedAssetError(
            "targeted image preparation requires a frozen filtered resume worklist"
        )
    mode = "apply" if apply else "dry-run"
    command = (
        python_executable,
        str(image_runner),
        "--mode",
        mode,
        "--catalog-snapshot-id",
        profile.catalog_snapshot_id,
        "--category-key",
        profile.category_key,
        "--theme",
        profile.theme_title,
        "--group-key",
        profile.group_key,
        "--batch-size",
        str(batch_size),
        "--batch-pause-seconds",
        f"{batch_pause_seconds:g}",
        "--max-workers",
        str(max_workers),
        "--run-dir",
        str(run_dir),
    )
    if apply:
        command += ("--confirm-catalog", profile.catalog_snapshot_id)
    return command


def _load_events(path: Path) -> list[dict[str, object]]:
    """Read a JSONL event stream while preserving its deterministic order."""

    events: list[dict[str, object]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise PreparedAssetError(f"preparation event log is unavailable: {path}") from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PreparedAssetError(
                f"preparation event log line {line_number} is invalid JSON"
            ) from exc
        if not isinstance(event, dict):
            raise PreparedAssetError(
                f"preparation event log line {line_number} is not an object"
            )
        events.append(event)
    return events


def _artifact_path(raw_path: object, *, run_dir: Path) -> Path:
    """Resolve one converter artifact and prevent path escape on resume."""

    if not isinstance(raw_path, str) or not raw_path:
        raise PreparedAssetError("prepared event has no SVG artifact path")
    path = Path(raw_path)
    candidate = path if path.is_absolute() else run_dir / path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise PreparedAssetError("prepared SVG path is outside run directory") from exc
    if not resolved.is_file():
        raise PreparedAssetError(f"prepared SVG artifact is missing: {resolved}")
    return resolved


def _event_key(event: dict[str, object]) -> tuple[str, str]:
    """Return the internal/source problem identity shared by paired events."""

    problem_id = event.get("problem_id")
    source_problem_id = event.get("source_problem_id")
    if not isinstance(problem_id, str) or not isinstance(source_problem_id, str):
        raise PreparedAssetError("asset event has incomplete problem identity")
    return problem_id, source_problem_id


def _indexed_asset_events(
    events: list[dict[str, object]],
    profile: GroupProfile,
) -> tuple[
    dict[tuple[str, str], dict[str, object]],
    dict[tuple[str, str], dict[str, object]],
]:
    """Index unique prepared and replaced events for the selected group."""

    prepared_by_key: dict[tuple[str, str], dict[str, object]] = {}
    replaced_by_key: dict[tuple[str, str], dict[str, object]] = {}
    for event in events:
        event_name = event.get("event")
        if event_name not in {"asset_prepared", "asset_replaced"}:
            continue
        if (
            event.get("group_key") != profile.group_key
            or event.get("asset_key") != "image_1"
        ):
            continue
        key = _event_key(event)
        collection = (
            prepared_by_key if event_name == "asset_prepared" else replaced_by_key
        )
        if key in collection:
            raise PreparedAssetError(f"duplicate {event_name} event for {key[1]}")
        collection[key] = event
    return prepared_by_key, replaced_by_key


def _prepared_record(
    target: ProblemTarget,
    prepared: dict[str, object],
    replaced: dict[str, object],
    context: _PreparationContext,
) -> PreparedGridPolygon:
    """Validate one paired event and build its frozen prepared record."""

    output_sha256 = prepared.get("output_sha256")
    if not isinstance(output_sha256, str) or (
        context.applied and replaced.get("output_sha256") != output_sha256
    ):
        raise PreparedAssetError("prepared/replaced output digest drifted")
    if context.applied and prepared.get("alt_text") != replaced.get("alt_text"):
        raise PreparedAssetError("prepared/replaced coordinate alt drifted")
    svg_path = _artifact_path(prepared.get("svg_path"), run_dir=context.run_dir)
    if hashlib.sha256(svg_path.read_bytes()).hexdigest() != output_sha256:
        raise PreparedAssetError("prepared SVG artifact digest drifted")
    alt_text = prepared.get("alt_text")
    if not isinstance(alt_text, str):
        raise PreparedAssetError("prepared event has no coordinate alt")
    if context.profile.expected_vertices is None:
        raise PreparedAssetError(
            "variable-vertex profiles require an existing SVG condition asset"
        )
    coordinates = parse_coordinate_alt(
        alt_text,
        expected_vertices=context.profile.expected_vertices,
    )
    validation = prepared.get("validation")
    if not isinstance(validation, dict):
        raise PreparedAssetError("prepared event has no validation object")
    if validation.get("vertices") != [list(point) for point in coordinates]:
        raise PreparedAssetError("prepared validation coordinates drifted")
    asset_id = (
        replaced.get("source_asset_id")
        if context.applied
        else f"preview-{target.problem_id}"
    )
    if not isinstance(asset_id, str) or not asset_id:
        raise PreparedAssetError("asset replacement has no readback asset identity")
    return PreparedGridPolygon(
        problem_id=target.problem_id,
        source_problem_id=target.source_problem_id,
        condition_asset_id=asset_id,
        condition_svg_path=svg_path,
        condition_svg_sha256=output_sha256,
        coordinates=coordinates,
        vertex_count=context.profile.expected_vertices,
        condition_was_replaced=True,
        converter_diagnostics={
            **validation,
            "input_sha256": prepared.get("input_sha256"),
            "converter_sha256": context.run_start.get("converter_sha256"),
            "template_sha256": context.run_start.get("template_sha256"),
        },
        ordered_coordinates=ordered_coordinates_from_svg(
            svg_path.read_bytes(),
            coordinates,
        ),
    )


def load_prepared_grid_polygons(
    events_path: Path,
    *,
    run_dir: Path,
    expected_targets: tuple[ProblemTarget, ...],
    profile: GroupProfile,
    applied: bool = True,
    allow_partial: bool = False,
) -> tuple[PreparedGridPolygon, ...]:
    """Validate paired converter events and return records in frozen target order."""

    events = _load_events(events_path)
    run_start = next(
        (event for event in events if event.get("event") == "run_start"),
        None,
    )
    if run_start is None:
        raise PreparedAssetError("preparation events have no run_start")
    if run_start.get("catalog_snapshot_id") != profile.catalog_snapshot_id:
        raise PreparedAssetError("preparation catalog identity drifted")
    transition = next(
        (
            event
            for event in events
            if event.get("event") == "group_transition"
            and event.get("group_key") == profile.group_key
        ),
        None,
    )
    if transition is None or transition.get("source_group_id") != profile.source_group_id:
        raise PreparedAssetError("preparation source group identity drifted")

    prepared_by_key, replaced_by_key = _indexed_asset_events(events, profile)

    expected_keys = {(target.problem_id, target.source_problem_id) for target in expected_targets}
    if not set(prepared_by_key) <= expected_keys or not set(replaced_by_key) <= expected_keys:
        raise PreparedAssetError("prepared/replaced event target set escaped expected scope")
    completed_keys = set(prepared_by_key) & set(replaced_by_key) if applied else set(prepared_by_key)
    if not allow_partial and completed_keys != expected_keys:
        raise PreparedAssetError("prepared/replaced event target set drifted")
    context = _PreparationContext(
        run_dir=run_dir,
        profile=profile,
        run_start=run_start,
        applied=applied,
    )
    return tuple(
        _prepared_record(
            target,
            prepared_by_key[key],
            replaced_by_key.get(key, {}),
            context,
        )
        for target in expected_targets
        if (key := (target.problem_id, target.source_problem_id)) in completed_keys
    )


def execute_image_preparation(
    executor: CommandExecutor,
    *,
    profile: GroupProfile,
    run_dir: Path,
    expected_targets: tuple[ProblemTarget, ...],
    apply: bool,
    only_source_problem_id: str | None = None,
    batch_size: int = 10,
    batch_pause_seconds: float = 0.0,
    max_workers: int = 10,
) -> tuple[PreparedGridPolygon, ...]:
    """Run the external image stage once and freeze its resulting events."""

    command = build_image_runner_command(
        profile,
        run_dir,
        apply=apply,
        only_source_problem_id=only_source_problem_id,
        batch_size=batch_size,
        batch_pause_seconds=batch_pause_seconds,
        max_workers=max_workers,
    )
    return_code = executor(command)
    if return_code not in {0, 2}:
        raise PreparedAssetError(
            f"image preparation runner failed with exit code {return_code}"
        )
    return load_prepared_grid_polygons(
        run_dir / "events.jsonl",
        run_dir=run_dir,
        expected_targets=expected_targets,
        profile=profile,
        applied=apply,
        allow_partial=True,
    )


def prepare_existing_svg(
    gateway: ExistingSvgGateway,
    target: ProblemTarget,
    *,
    artifact_dir: Path,
    profile: GroupProfile,
    apply: bool,
) -> PreparedGridPolygon:
    """Download, parse, optionally repair alt, and freeze one existing SVG once."""

    asset = gateway.download_existing_svg(target)
    if asset.content_type != "image/svg+xml":
        raise PreparedAssetError("existing condition asset is not SVG")
    parsed = parse_grid_polygon(
        asset.svg_bytes,
        expected_vertices=profile.expected_vertices,
        geometry_profile=profile.strategy_key,
        snap_tolerance=profile.grid_snap_tolerance,
    )
    canonical_alt = serialize_coordinate_alt(parsed.coordinates)
    replaced = False
    if asset.alt_text != canonical_alt and apply:
        asset = gateway.replace_existing_svg_alt(target, asset, canonical_alt)
        if asset.alt_text != canonical_alt:
            raise PreparedAssetError("existing SVG alt readback drifted")
        replaced = True
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = (artifact_dir / f"{target.source_problem_id}-condition.svg").resolve()
    artifact_path.write_bytes(asset.svg_bytes)
    digest = polygon_sha256(asset.svg_bytes)
    return PreparedGridPolygon(
        problem_id=target.problem_id,
        source_problem_id=target.source_problem_id,
        condition_asset_id=asset.asset_id,
        condition_svg_path=artifact_path,
        condition_svg_sha256=digest,
        coordinates=parsed.coordinates,
        vertex_count=len(parsed.coordinates),
        condition_was_replaced=replaced,
        converter_diagnostics={
            "source": "existing-svg",
            "grid_step_x": parsed.grid_step_x,
            "grid_step_y": parsed.grid_step_y,
            "discarded_intermediate_points": parsed.discarded_intermediate_points,
        },
        ordered_coordinates=parsed.coordinates,
    )
