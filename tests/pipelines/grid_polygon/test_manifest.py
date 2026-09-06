"""Protect frozen prepared-manifest identity and artifact drift guards."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from pathlib import Path
import shutil

import pytest

from solution_runner.pipelines.grid_polygon.asset_preparation import load_prepared_grid_polygons
from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.manifest import (
    FrozenRunScope,
    ManifestDriftError,
    read_prepared_manifest,
    write_prepared_manifest,
)
from solution_runner.pipelines.core.models import PreparedGridRing, ProblemTarget


FIXTURE_DIR = Path(__file__).with_name("fixtures")
TARGET = ProblemTarget(
    problem_id="154ea49f-043f-4f0d-bf37-827df2a0d335",
    source_problem_id="247697",
    source_group_id="96309f98-73c1-4abc-8005-73a4307e7295",
    group_key="27547",
    problem_order_index=2,
)


def _scope() -> FrozenRunScope:
    """Return the fixed source scope represented by the manifest fixture."""

    profile = get_group_profile("27547")
    return FrozenRunScope(
        catalog_snapshot_id=profile.catalog_snapshot_id,
        snapshot_theme_id=profile.snapshot_theme_id,
        source_group_id=profile.source_group_id,
        group_key=profile.group_key,
        target_problem_ids=(TARGET.problem_id,),
    )


def _prepared_record(tmp_path: Path):
    """Build one prepared record from the recorded converter events."""

    run_dir = tmp_path / "run"
    artifact = run_dir / "artifacts" / "247697-condition.svg"
    artifact.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_DIR / "legacy_intermediate_vertex.svg", artifact)
    shutil.copyfile(FIXTURE_DIR / "image_apply_events.jsonl", run_dir / "events.jsonl")
    record = load_prepared_grid_polygons(
        run_dir / "events.jsonl",
        run_dir=run_dir,
        expected_targets=(TARGET,),
        profile=get_group_profile("27547"),
    )[0]
    return run_dir, record


def test_manifest_round_trip_uses_relative_artifact_paths(tmp_path: Path) -> None:
    """Catch machine-specific absolute paths or loss of frozen geometry."""

    run_dir, record = _prepared_record(tmp_path)
    manifest_path = run_dir / "prepared-manifest.json"
    write_prepared_manifest(manifest_path, _scope(), (record,))

    assert str(run_dir) not in manifest_path.read_text(encoding="utf-8")
    loaded = read_prepared_manifest(manifest_path, expected_scope=_scope())
    assert loaded == (record,)


def test_manifest_rejects_scope_digest_and_coordinate_drift(tmp_path: Path) -> None:
    """Catch resume against a different catalog or modified prepared artifact."""

    run_dir, record = _prepared_record(tmp_path)
    manifest_path = run_dir / "prepared-manifest.json"
    write_prepared_manifest(manifest_path, _scope(), (record,))

    with pytest.raises(ManifestDriftError, match="scope"):
        read_prepared_manifest(
            manifest_path,
            expected_scope=replace(_scope(), group_key="27546"),
        )

    record.condition_svg_path.write_bytes(b"changed")
    with pytest.raises(ManifestDriftError, match="digest"):
        read_prepared_manifest(manifest_path, expected_scope=_scope())


def test_manifest_round_trips_ring_geometry(tmp_path: Path) -> None:
    """Preserve exact annulus radii across a solution-stage resume."""

    import hashlib

    run_dir = tmp_path / "ring-run"
    artifact = run_dir / "artifacts" / "263425.svg"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("<svg></svg>", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    record = PreparedGridRing(
        problem_id="problem-263425",
        source_problem_id="263425",
        condition_asset_id="ring-asset",
        condition_svg_path=artifact,
        condition_svg_sha256=digest,
        center=(5, 5),
        outer_point=(8, 8),
        inner_point=(6, 8),
        outer_radius_squared=18,
        inner_radius_squared=10,
        condition_was_replaced=True,
        converter_diagnostics={"shape_type": "ring"},
        inner_center=(6, 5),
        ring_alignment="offset",
        known_circle_area="inner",
        given_circle_area=Fraction(23, 2),
    )
    scope = FrozenRunScope(
        catalog_snapshot_id="4073fc7b-2056-4697-b18b-38741c94d0f4",
        snapshot_theme_id="d50df164-ea7e-4058-a5b5-8d665c586cf3",
        source_group_id="35a2b971-d6d3-4013-817b-5dd44a4e9c65",
        group_key="245008",
        target_problem_ids=(record.problem_id,),
    )
    manifest_path = run_dir / "prepared-manifest.json"

    write_prepared_manifest(manifest_path, scope, (record,))

    assert read_prepared_manifest(manifest_path, expected_scope=scope) == (record,)
