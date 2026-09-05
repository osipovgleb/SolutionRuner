"""Verify content-sniffed and target-isolated ring asset preparation."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.models import ProblemTarget
from solution_runner.pipelines.grid_polygon.ring_asset_preparation import (
    ConditionAsset,
    RingAssetPreparationError,
    detect_known_circle_area,
    prepare_ring_assets,
    sniff_asset_kind,
)


def test_asset_kind_uses_bytes_instead_of_declared_extension_or_mime() -> None:
    """Recognize a saved SVG even when its source metadata says PNG."""

    assert sniff_asset_kind(b"<?xml version='1.0'?><svg></svg>", "image/png") == "svg"
    assert sniff_asset_kind(b"\x89PNG\r\n\x1a\nrest", "image/svg+xml") == "raster"


@pytest.mark.parametrize(
    ("condition_html", "expected_side", "expected_area"),
    (
        ("<p>Площадь внут\u00adреннего круга равна 46.</p>", "inner", Fraction(46)),
        ("<p>Площадь внешнего круга равна 12,5.</p>", "outer", Fraction(25, 2)),
    ),
)
def test_known_circle_area_is_detected_from_each_problem_condition(
    condition_html: str,
    expected_side: str,
    expected_area: Fraction,
) -> None:
    """Detect the known circle per task without encoding it in a group profile."""

    assert detect_known_circle_area(condition_html) == (expected_side, expected_area)


@pytest.mark.parametrize(
    "condition_html",
    (
        "<p>Найдите площадь кольца.</p>",
        "<p>Площадь внутреннего круга равна 4, внешнего круга равна 16.</p>",
    ),
)
def test_known_circle_area_rejects_missing_or_ambiguous_conditions(
    condition_html: str,
) -> None:
    """Fail one task closed when the given area cannot be identified uniquely."""

    with pytest.raises(RingAssetPreparationError, match="known circle area"):
        detect_known_circle_area(condition_html)


_TARGET = ProblemTarget(
    problem_id="problem-263425",
    source_problem_id="263425",
    source_group_id="35a2b971-d6d3-4013-817b-5dd44a4e9c65",
    group_key="245008",
    problem_order_index=3,
)


def _ring_svg() -> bytes:
    """Return one converter-shaped lattice annulus SVG."""

    return b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
      <line x1="0" y1="0" x2="0" y2="200"/>
      <line x1="20" y1="0" x2="20" y2="200"/>
      <line x1="0" y1="0" x2="200" y2="0"/>
      <line x1="0" y1="20" x2="200" y2="20"/>
      <g id="ring-outline">
        <circle cx="100" cy="100" r="84.852814"/>
        <circle cx="100" cy="100" r="63.245553"/>
      </g>
    </svg>'''


class _Gateway:
    """Record one ring condition download, upload, replacement, and readback."""

    def __init__(self, asset: ConditionAsset) -> None:
        """Store one current condition asset."""

        self.asset = asset
        self.uploads = 0
        self.replacements = 0

    def download_original_condition_asset(self, target: ProblemTarget) -> ConditionAsset:
        """Return the original condition asset once."""

        assert target == _TARGET
        return self.asset

    def get_problem_context(self, problem_id: str) -> dict[str, object]:
        """Return one task-local known-area condition for the new strategy."""

        assert problem_id == _TARGET.problem_id
        return {
            "normalized_content": {
                "sections": [
                    {
                        "key": "condition",
                        "html": "<p>Площадь внутреннего круга равна 46.</p>",
                    }
                ]
            }
        }

    def upload_condition_svg(
        self,
        *,
        source_problem_id: str,
        svg_bytes: bytes,
        sha256: str,
    ) -> dict[str, str]:
        """Return a fixed uploaded source-asset identity."""

        assert source_problem_id == "263425" and svg_bytes == _ring_svg()
        self.uploads += 1
        return {"source_asset_id": "new-ring", "sha256": sha256}

    def replace_condition_asset(
        self,
        target: ProblemTarget,
        *,
        replacement_asset_id: str,
        alt_text: str,
    ) -> dict[str, str]:
        """Return authoritative replacement readback."""

        assert target == _TARGET and replacement_asset_id == "new-ring"
        assert "R₁²=18" in alt_text and "R₂²=10" in alt_text
        self.replacements += 1
        return {"asset_id": replacement_asset_id, "alt": alt_text}


def test_existing_svg_is_prepared_without_conversion_or_write(tmp_path: Path) -> None:
    """Consume a real SVG payload once even when its MIME metadata says PNG."""

    gateway = _Gateway(
        ConditionAsset("legacy-ring", "image/png", "", _ring_svg())
    )
    converter_calls = 0

    def converter(_source: Path, _output_dir: Path):
        """Fail if an SVG is needlessly passed through raster conversion."""

        nonlocal converter_calls
        converter_calls += 1
        raise AssertionError("converter must not run")

    prepared = prepare_ring_assets(
        gateway,
        profile=get_group_profile("245008"),
        run_dir=tmp_path,
        expected_targets=(_TARGET,),
        apply=False,
        max_workers=10,
        converter=converter,
    )

    assert converter_calls == gateway.uploads == gateway.replacements == 0
    assert prepared[0].outer_radius_squared == 18
    assert prepared[0].inner_radius_squared == 10
    assert prepared[0].condition_was_replaced is False


def test_raster_is_converted_uploaded_replaced_and_verified_once(tmp_path: Path) -> None:
    """Use one raster conversion and one exact asset replacement in apply mode."""

    gateway = _Gateway(
        ConditionAsset("old-raster", "image/png", "", b"\x89PNG\r\n\x1a\nrest")
    )
    converter_calls = 0

    def converter(source: Path, output_dir: Path):
        """Write one deterministic converter artifact and diagnostic record."""

        nonlocal converter_calls
        converter_calls += 1
        assert source.read_bytes().startswith(b"\x89PNG")
        artifact = output_dir / "263425.svg"
        output_dir.mkdir(parents=True, exist_ok=True)
        artifact.write_bytes(_ring_svg())
        return artifact, {
            "shape_type": "ring",
            "outer_radius_squared": "18",
            "inner_radius_squared": "10",
        }

    prepared = prepare_ring_assets(
        gateway,
        profile=get_group_profile("245008"),
        run_dir=tmp_path,
        expected_targets=(_TARGET,),
        apply=True,
        converter=converter,
    )

    assert converter_calls == gateway.uploads == gateway.replacements == 1
    assert prepared[0].condition_asset_id == "new-ring"
    assert prepared[0].condition_was_replaced is True


def test_known_area_profile_freezes_detected_condition_and_alignment(tmp_path: Path) -> None:
    """Carry task-varying condition and geometry facts into the fixed manifest."""

    profile = replace(
        get_group_profile("245008"),
        strategy_key="annulus-from-known-area",
        solution_scope="missing_only",
        existing_solution_policy="preserve",
    )
    gateway = _Gateway(ConditionAsset("legacy-ring", "image/svg+xml", "", _ring_svg()))

    prepared = prepare_ring_assets(
        gateway,
        profile=profile,
        run_dir=tmp_path,
        expected_targets=(_TARGET,),
        apply=False,
    )[0]

    assert prepared.known_circle_area == "inner"
    assert prepared.given_circle_area == Fraction(46)
    assert prepared.ring_alignment == "concentric"
    assert prepared.inner_center == prepared.center
