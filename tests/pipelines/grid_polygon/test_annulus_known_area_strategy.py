"""Verify annulus solutions derived from a per-task known circle area."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest

from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.models import PreparedGridRing
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy
from solution_runner.pipelines.grid_polygon.strategies.protocol import StrategyError


def _prepared(tmp_path: Path, *, known_side: str, given_area: Fraction) -> PreparedGridRing:
    """Return an offset nested ring with exact squared radii 16 and 4."""

    artifact = tmp_path / "ring.svg"
    artifact.write_text("<svg></svg>", encoding="utf-8")
    return PreparedGridRing(
        problem_id="problem-child",
        source_problem_id="315235",
        condition_asset_id="asset",
        condition_svg_path=artifact,
        condition_svg_sha256="sha",
        center=(5, 5),
        outer_point=(1, 5),
        inner_point=(8, 5),
        outer_radius_squared=16,
        inner_radius_squared=4,
        condition_was_replaced=False,
        converter_diagnostics={},
        inner_center=(6, 5),
        ring_alignment="offset",
        known_circle_area=known_side,
        given_circle_area=given_area,
    )


@pytest.mark.parametrize(
    ("known_side", "given_area", "expected"),
    (
        ("inner", Fraction(46), Fraction(138)),
        ("outer", Fraction(100), Fraction(75)),
    ),
)
def test_known_area_annulus_strategy_handles_both_given_circle_sides(
    tmp_path: Path,
    known_side: str,
    given_area: Fraction,
    expected: Fraction,
) -> None:
    """Calculate the shaded ring from the actual radius ratio and given area."""

    strategy = get_solution_strategy("annulus-from-known-area")
    profile = get_group_profile("315122")
    analysis = strategy.analyze(
        _prepared(tmp_path, known_side=known_side, given_area=given_area),
        profile,
    )

    assert strategy.requires_solution_diagram is False
    assert analysis.area == analysis.area_by_coordinates == expected
    assert analysis.details["ring_alignment"] == "offset"
    solution = strategy.build_solution_html(analysis, profile)
    assert "Площади кругов относятся как квадраты их радиусов" in solution
    assert r"\frac{R^2}{r^2}=\frac{16}{4}=4" in solution
    assert strategy.build_answer_html(analysis).endswith(f">{int(expected)}</span></p>")


def test_known_area_annulus_strategy_requires_task_detection(tmp_path: Path) -> None:
    """Reject a prepared ring whose condition facts were not identified."""

    prepared = replace(
        _prepared(tmp_path, known_side="inner", given_area=Fraction(46)),
        known_circle_area=None,
        given_circle_area=None,
    )

    with pytest.raises(StrategyError, match="known circle area"):
        get_solution_strategy("annulus-from-known-area").analyze(
            prepared,
            get_group_profile("315122"),
        )


def test_known_area_annulus_strategy_displays_non_half_radius_ratio(tmp_path: Path) -> None:
    """Keep exact quarter ratios in prose while allowing a half-integer answer."""

    prepared = replace(
        _prepared(tmp_path, known_side="inner", given_area=Fraction(46)),
        outer_point=(1, 5),
        inner_point=(8, 5),
        outer_radius_squared=25,
        inner_radius_squared=4,
    )
    strategy = get_solution_strategy("annulus-from-known-area")
    profile = get_group_profile("315122")
    analysis = strategy.analyze(prepared, profile)

    assert analysis.area == Fraction(483, 2)
    assert r"\frac{25}{4}" in strategy.build_solution_html(analysis, profile)
    assert strategy.build_answer_html(analysis) == (
        '<p><span data-effect="spaced">241,5</span></p>'
    )


def test_known_area_annulus_strategy_keeps_exact_quarter_answer(tmp_path: Path) -> None:
    """Represent terminating quarter answers used by real known-area tasks."""

    prepared = replace(
        _prepared(tmp_path, known_side="inner", given_area=Fraction(77)),
        outer_radius_squared=25,
        inner_radius_squared=4,
    )
    strategy = get_solution_strategy("annulus-from-known-area")
    profile = get_group_profile("315122")
    analysis = strategy.analyze(prepared, profile)

    assert analysis.area == Fraction(1617, 4)
    assert "404{,}25" in strategy.build_solution_html(analysis, profile)
    assert strategy.build_answer_html(analysis) == (
        '<p><span data-effect="spaced">404,25</span></p>'
    )
