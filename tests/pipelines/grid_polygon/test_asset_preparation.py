"""Protect one-pass conversion events and existing-SVG preparation."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from solution_runner.pipelines.grid_polygon.asset_preparation import (
    ExistingSvgAsset,
    PreparedAssetError,
    execute_image_preparation,
    load_prepared_grid_polygons,
    prepare_existing_svg,
)
from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.models import ProblemTarget


FIXTURE_DIR = Path(__file__).with_name("fixtures")
TARGET = ProblemTarget(
    problem_id="154ea49f-043f-4f0d-bf37-827df2a0d335",
    source_problem_id="247697",
    source_group_id="96309f98-73c1-4abc-8005-73a4307e7295",
    group_key="27547",
    problem_order_index=2,
)


def _prepared_run_dir(tmp_path: Path) -> Path:
    """Create one local run directory matching the recorded event contract."""

    run_dir = tmp_path / "image-apply"
    artifact = run_dir / "artifacts" / "247697-condition.svg"
    artifact.parent.mkdir(parents=True)
    shutil.copyfile(FIXTURE_DIR / "legacy_intermediate_vertex.svg", artifact)
    shutil.copyfile(FIXTURE_DIR / "image_apply_events.jsonl", run_dir / "events.jsonl")
    return run_dir


def test_converter_events_become_one_frozen_record(tmp_path: Path) -> None:
    """Catch a second download/parse path or loss of converter event evidence."""

    run_dir = _prepared_run_dir(tmp_path)
    records = load_prepared_grid_polygons(
        run_dir / "events.jsonl",
        run_dir=run_dir,
        expected_targets=(TARGET,),
        profile=get_group_profile("27547"),
    )

    assert len(records) == 1
    assert records[0].coordinates == ((3, 1), (1, 10), (3, 7))
    assert records[0].condition_asset_id == "c98725f8-dc45-4a5f-b3fa-c8a752a61c0a"
    assert records[0].condition_was_replaced is True
    assert records[0].converter_diagnostics["converter_sha256"].startswith("08600e")


def test_event_pair_rejects_digest_identity_and_path_drift(tmp_path: Path) -> None:
    """Catch reuse of events that no longer identify the frozen SVG target."""

    run_dir = _prepared_run_dir(tmp_path)
    rows = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    prepared = next(row for row in rows if row["event"] == "asset_prepared")
    prepared["output_sha256"] = "f" * 64
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(PreparedAssetError, match="digest"):
        load_prepared_grid_polygons(
            run_dir / "events.jsonl",
            run_dir=run_dir,
            expected_targets=(TARGET,),
            profile=get_group_profile("27547"),
        )

    prepared["output_sha256"] = "9dc08da9d23aaa05350f8ba34590e5cc49174dde23cdee673ac91ab903230a1f"
    prepared["svg_path"] = "../outside.svg"
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(PreparedAssetError, match="outside run directory"):
        load_prepared_grid_polygons(
            run_dir / "events.jsonl",
            run_dir=run_dir,
            expected_targets=(TARGET,),
            profile=get_group_profile("27547"),
        )


def test_image_preparation_executes_converter_runner_once(tmp_path: Path) -> None:
    """Catch the former dry-run plus apply duplicate conversion behavior."""

    run_dir = _prepared_run_dir(tmp_path)
    commands: list[tuple[str, ...]] = []

    def executor(argv: tuple[str, ...]) -> int:
        """Record the one external command without running a process."""

        commands.append(argv)
        return 0

    records = execute_image_preparation(
        executor,
        profile=get_group_profile("27547"),
        run_dir=run_dir,
        expected_targets=(TARGET,),
        apply=True,
    )

    assert len(commands) == 1
    assert "mcp_grid_polygon_transformations.py" in commands[0][1]
    worker_index = commands[0].index("--max-workers")
    assert commands[0][worker_index + 1] == "10"
    assert records[0].source_problem_id == "247697"


class _ExistingSvgGateway:
    """Record the narrow asset operations required by existing-SVG preparation."""

    def __init__(self, svg_bytes: bytes, alt_text: str = "") -> None:
        """Initialize one fixed source asset and call counters."""

        self.asset = ExistingSvgAsset(
            asset_id="legacy-asset",
            content_type="image/svg+xml",
            alt_text=alt_text,
            svg_bytes=svg_bytes,
        )
        self.download_calls = 0
        self.replace_calls = 0

    def download_existing_svg(self, target: ProblemTarget) -> ExistingSvgAsset:
        """Return the fixed SVG and record its single download."""

        assert target == TARGET
        self.download_calls += 1
        return self.asset

    def replace_existing_svg_alt(
        self,
        target: ProblemTarget,
        asset: ExistingSvgAsset,
        alt_text: str,
    ) -> ExistingSvgAsset:
        """Return readback with canonical alt and record the metadata write."""

        assert target == TARGET
        self.replace_calls += 1
        self.asset = replace(asset, alt_text=alt_text)
        return self.asset


def test_existing_svg_is_downloaded_and_parsed_once(tmp_path: Path) -> None:
    """Catch solution-stage redownload or converter use for an existing SVG."""

    gateway = _ExistingSvgGateway(
        (FIXTURE_DIR / "legacy_intermediate_vertex.svg").read_bytes()
    )
    prepared = prepare_existing_svg(
        gateway,
        TARGET,
        artifact_dir=tmp_path / "legacy-svg",
        profile=get_group_profile("27547"),
        apply=True,
    )

    assert gateway.download_calls == 1
    assert gateway.replace_calls == 1
    assert prepared.coordinates == ((3, 1), (1, 10), (3, 7))
    assert prepared.condition_svg_path.read_bytes() == gateway.asset.svg_bytes
