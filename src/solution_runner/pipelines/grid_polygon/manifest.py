"""Persist and validate restartable prepared grid-polygon manifests."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
import hashlib
import json
from pathlib import Path

from ..core.models import PreparedFigure, PreparedGridPolygon, PreparedGridRing
from .geometry.grid_polygon import GridPolygonError, ordered_coordinates_from_svg


class ManifestDriftError(RuntimeError):
    """Report a resume artifact that no longer matches its frozen scope."""


@dataclass(frozen=True)
class FrozenRunScope:
    """Identify the exact catalog, group, and ordered target set for one run."""

    catalog_snapshot_id: str
    snapshot_theme_id: str
    source_group_id: str
    group_key: str
    target_problem_ids: tuple[str, ...]


def _record_payload(record: PreparedFigure, *, run_dir: Path) -> dict[str, object]:
    """Serialize one prepared record with an in-run relative artifact path."""

    resolved = record.condition_svg_path.resolve()
    try:
        relative = resolved.relative_to(run_dir.resolve())
    except ValueError as exc:
        raise ManifestDriftError("prepared artifact is outside manifest run directory") from exc
    payload: dict[str, object] = {
        "problem_id": record.problem_id,
        "source_problem_id": record.source_problem_id,
        "condition_asset_id": record.condition_asset_id,
        "condition_svg_path": relative.as_posix(),
        "condition_svg_sha256": record.condition_svg_sha256,
        "condition_was_replaced": record.condition_was_replaced,
        "converter_diagnostics": dict(record.converter_diagnostics),
    }
    if isinstance(record, PreparedGridRing):
        payload.update(
            geometry_kind="ring",
            center=list(record.center),
            outer_point=list(record.outer_point),
            inner_point=list(record.inner_point),
            outer_radius_squared=record.outer_radius_squared,
            inner_radius_squared=record.inner_radius_squared,
            inner_center=list(record.inner_center or record.center),
            ring_alignment=record.ring_alignment,
            known_circle_area=record.known_circle_area,
            given_circle_area=(
                str(record.given_circle_area)
                if record.given_circle_area is not None
                else None
            ),
        )
    else:
        payload.update(
            geometry_kind="polygon",
            coordinates=[list(point) for point in record.coordinates],
            ordered_coordinates=[list(point) for point in record.geometry_coordinates],
            vertex_count=record.vertex_count,
        )
    return payload


def write_prepared_manifest(
    path: Path,
    scope: FrozenRunScope,
    records: tuple[PreparedFigure, ...],
) -> None:
    """Write one deterministic manifest after validating record target order."""

    if tuple(record.problem_id for record in records) != scope.target_problem_ids:
        raise ManifestDriftError("prepared record order does not match frozen scope")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "scope": asdict(scope),
        "records": [_record_payload(record, run_dir=path.parent) for record in records],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _scope_payload(scope: FrozenRunScope) -> dict[str, object]:
    """Return the JSON-shaped scope used for strict resume comparison."""

    payload = asdict(scope)
    payload["target_problem_ids"] = list(scope.target_problem_ids)
    return payload


def read_prepared_manifest(
    path: Path,
    *,
    expected_scope: FrozenRunScope,
    allow_target_subset: bool = False,
) -> tuple[PreparedFigure, ...]:
    """Load prepared records only when scope, identities, and artifacts agree."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestDriftError("prepared manifest is unreadable") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ManifestDriftError("prepared manifest schema is unsupported")
    actual_scope = payload.get("scope")
    expected_payload = _scope_payload(expected_scope)
    if not isinstance(actual_scope, dict):
        raise ManifestDriftError("prepared manifest scope drifted")
    actual_target_ids = actual_scope.get("target_problem_ids")
    expected_target_ids = expected_payload.pop("target_problem_ids")
    actual_without_targets = {
        key: value for key, value in actual_scope.items() if key != "target_problem_ids"
    }
    if (
        actual_without_targets != expected_payload
        or not isinstance(actual_target_ids, list)
        or not all(isinstance(value, str) for value in actual_target_ids)
    ):
        raise ManifestDriftError("prepared manifest scope drifted")
    if allow_target_subset:
        positions = {
            problem_id: index for index, problem_id in enumerate(expected_target_ids)
        }
        actual_positions = [positions.get(problem_id, -1) for problem_id in actual_target_ids]
        if (
            len(positions) != len(expected_target_ids)
            or len(set(actual_target_ids)) != len(actual_target_ids)
            or any(position < 0 for position in actual_positions)
            or actual_positions != sorted(actual_positions)
        ):
            raise ManifestDriftError("prepared manifest target scope drifted")
    elif actual_target_ids != expected_target_ids:
        raise ManifestDriftError("prepared manifest scope drifted")
    raw_records = payload.get("records")
    if not isinstance(raw_records, list):
        raise ManifestDriftError("prepared manifest records are invalid")
    records: list[PreparedFigure] = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise ManifestDriftError("prepared manifest record is invalid")
        relative = raw.get("condition_svg_path")
        if not isinstance(relative, str):
            raise ManifestDriftError("prepared manifest artifact path is invalid")
        artifact = (path.parent / relative).resolve()
        try:
            artifact.relative_to(path.parent.resolve())
        except ValueError as exc:
            raise ManifestDriftError("prepared manifest artifact escapes run directory") from exc
        if not artifact.is_file():
            raise ManifestDriftError("prepared manifest artifact is missing")
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if digest != raw.get("condition_svg_sha256"):
            raise ManifestDriftError("prepared manifest artifact digest drifted")
        diagnostics = raw.get("converter_diagnostics")
        if not isinstance(diagnostics, dict):
            raise ManifestDriftError("prepared manifest diagnostics are invalid")
        geometry_kind = str(raw.get("geometry_kind") or "polygon")
        if geometry_kind == "ring":
            try:
                center = tuple(int(value) for value in raw["center"])
                outer_point = tuple(int(value) for value in raw["outer_point"])
                inner_point = tuple(int(value) for value in raw["inner_point"])
                outer_squared = int(raw["outer_radius_squared"])
                inner_squared = int(raw["inner_radius_squared"])
                inner_center = tuple(int(value) for value in raw.get("inner_center", center))
                alignment = str(raw.get("ring_alignment") or "concentric")
                known_circle_area = raw.get("known_circle_area")
                raw_given_area = raw.get("given_circle_area")
                given_circle_area = (
                    Fraction(str(raw_given_area)) if raw_given_area is not None else None
                )
                if not (
                    len(center) == len(inner_center) == len(outer_point) == len(inner_point) == 2
                    and 0 < inner_squared < outer_squared
                    and alignment in {"concentric", "offset"}
                    and known_circle_area in {None, "inner", "outer"}
                    and (given_circle_area is None or given_circle_area > 0)
                ):
                    raise ValueError
                record: PreparedFigure = PreparedGridRing(
                    problem_id=str(raw["problem_id"]),
                    source_problem_id=str(raw["source_problem_id"]),
                    condition_asset_id=str(raw["condition_asset_id"]),
                    condition_svg_path=artifact,
                    condition_svg_sha256=digest,
                    center=(center[0], center[1]),
                    outer_point=(outer_point[0], outer_point[1]),
                    inner_point=(inner_point[0], inner_point[1]),
                    outer_radius_squared=outer_squared,
                    inner_radius_squared=inner_squared,
                    condition_was_replaced=bool(raw["condition_was_replaced"]),
                    converter_diagnostics=diagnostics,
                    inner_center=(inner_center[0], inner_center[1]),
                    ring_alignment=alignment,
                    known_circle_area=known_circle_area,
                    given_circle_area=given_circle_area,
                )
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                raise ManifestDriftError("prepared manifest ring geometry is invalid") from exc
        elif geometry_kind == "polygon":
            try:
                coordinates = tuple(
                    (int(point[0]), int(point[1])) for point in raw["coordinates"]
                )
                vertex_count = int(raw["vertex_count"])
            except (KeyError, TypeError, ValueError, IndexError) as exc:
                raise ManifestDriftError("prepared manifest coordinates are invalid") from exc
            if len(coordinates) != vertex_count or len(set(coordinates)) != vertex_count:
                raise ManifestDriftError("prepared manifest coordinates drifted")
            try:
                raw_ordered = raw.get("ordered_coordinates")
                ordered_coordinates = (
                    tuple((int(point[0]), int(point[1])) for point in raw_ordered)
                    if raw_ordered is not None
                    else ordered_coordinates_from_svg(artifact.read_bytes(), coordinates)
                )
            except (TypeError, ValueError, IndexError, GridPolygonError) as exc:
                raise ManifestDriftError("prepared manifest ordered coordinates are invalid") from exc
            if len(ordered_coordinates) != vertex_count or len(set(ordered_coordinates)) != vertex_count:
                raise ManifestDriftError("prepared manifest ordered coordinates drifted")
            try:
                record = PreparedGridPolygon(
                    problem_id=str(raw["problem_id"]),
                    source_problem_id=str(raw["source_problem_id"]),
                    condition_asset_id=str(raw["condition_asset_id"]),
                    condition_svg_path=artifact,
                    condition_svg_sha256=digest,
                    coordinates=coordinates,
                    vertex_count=vertex_count,
                    condition_was_replaced=bool(raw["condition_was_replaced"]),
                    converter_diagnostics=diagnostics,
                    ordered_coordinates=ordered_coordinates,
                )
            except KeyError as exc:
                raise ManifestDriftError("prepared manifest identity is incomplete") from exc
        else:
            raise ManifestDriftError("prepared manifest geometry kind is unsupported")
        records.append(record)
    if [record.problem_id for record in records] != actual_target_ids:
        raise ManifestDriftError("prepared manifest target identity drifted")
    return tuple(records)
