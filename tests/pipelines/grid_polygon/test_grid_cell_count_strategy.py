"""Verify the reusable exact cell-count strategy for grid-aligned figures."""

from __future__ import annotations

from pathlib import Path

from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.models import PreparedGridPolygon
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy


def _prepared(tmp_path: Path) -> PreparedGridPolygon:
    """Return one minimized C-shaped condition with eleven unit cells."""

    coordinates = (
        (1, 1),
        (1, 5),
        (5, 5),
        (5, 4),
        (3, 4),
        (3, 2),
        (4, 2),
        (4, 1),
    )
    svg_path = tmp_path / "grid-cell-count.svg"
    svg_path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 140 140">'
        '<polygon points="20,20 20,100 100,100 100,80 60,80 60,40 '
        '80,40 80,20" fill="#8da3cc" stroke="#111"/>'
        "</svg>",
        encoding="utf-8",
    )
    return PreparedGridPolygon(
        problem_id="problem-401457",
        source_problem_id="401457",
        condition_asset_id="condition-asset",
        condition_svg_path=svg_path,
        condition_svg_sha256="fixture",
        coordinates=coordinates,
        vertex_count=len(coordinates),
        condition_was_replaced=False,
        converter_diagnostics={},
    )


def test_grid_cell_count_matches_coordinate_area_and_parent_wording(
    tmp_path: Path,
) -> None:
    """Count unit cells independently and keep the exact prototype sentence."""

    profile = get_group_profile("341675")
    strategy = get_solution_strategy(profile.strategy_key)
    prepared = _prepared(tmp_path)

    analysis = strategy.analyze(prepared, profile)

    assert analysis.area == 11
    assert analysis.area_by_coordinates == 11
    assert analysis.details["cell_count"] == 11
    assert strategy.requires_solution_diagram is False
    assert strategy.build_formula(analysis, profile) == "S=11"
    assert strategy.build_solution_html(analysis, profile) == (
        "<p>Посчитаем количество клеток внутри закрашенной области: их 11.</p>"
    )
    assert strategy.build_answer_html(analysis) == (
        '<p><span data-effect="spaced">11</span></p>'
    )


def test_grid_cell_count_rejects_a_non_axis_aligned_boundary(tmp_path: Path) -> None:
    """Refuse to describe a diagonal figure as a union of whole cells."""

    prepared = _prepared(tmp_path)
    invalid = PreparedGridPolygon(
        **{
            **prepared.__dict__,
            "coordinates": ((1, 1), (1, 5), (5, 5), (4, 1)),
            "vertex_count": 4,
        }
    )
    profile = get_group_profile("341675")
    strategy = get_solution_strategy(profile.strategy_key)

    try:
        strategy.analyze(invalid, profile)
    except ValueError as exc:
        assert "axis-aligned" in str(exc)
    else:
        raise AssertionError("non-axis-aligned cell figure was accepted")
