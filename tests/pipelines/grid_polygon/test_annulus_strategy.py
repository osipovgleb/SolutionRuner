"""Verify exact annulus geometry, prose, and deterministic solution diagrams."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.models import PreparedGridRing
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy


def _prepared_ring(tmp_path: Path) -> PreparedGridRing:
    """Return one ring with lattice radii squared 18 and 10."""

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
        '<g id="ring-outline" fill="none" stroke="#143B8F">'
        '<circle cx="100" cy="100" r="84.852814"/>'
        '<circle cx="100" cy="100" r="63.245553"/>'
        '</g></svg>'
    )
    path = tmp_path / "ring.svg"
    path.write_text(svg, encoding="utf-8")
    return PreparedGridRing(
        problem_id="problem-263425",
        source_problem_id="263425",
        condition_asset_id="condition-263425",
        condition_svg_path=path,
        condition_svg_sha256="condition-sha",
        center=(5, 5),
        outer_point=(8, 8),
        inner_point=(6, 8),
        outer_radius_squared=18,
        inner_radius_squared=10,
        condition_was_replaced=True,
        converter_diagnostics={
            "svg_center": [100.0, 100.0],
            "svg_outer_radius": 84.852814,
            "svg_inner_radius": 63.245553,
            "grid_cell_size": 20.0,
        },
    )


def test_annulus_strategy_uses_exact_lattice_radius_squares(tmp_path: Path) -> None:
    """Compute S/pi from independent center-to-lattice-point distances."""

    prepared = _prepared_ring(tmp_path)
    profile = get_group_profile("245008")
    strategy = get_solution_strategy("annulus-area")

    analysis = strategy.analyze(prepared, profile)

    assert analysis.area == analysis.area_by_coordinates == Fraction(8)
    assert analysis.details["outer_radius_squared"] == 18
    assert analysis.details["inner_radius_squared"] == 10
    assert strategy.build_answer_html(analysis) == (
        '<p><span data-effect="spaced">8</span></p>'
    )
    solution = strategy.build_solution_html(analysis, profile)
    assert r"R_1^2=3^2+3^2=18" in solution
    assert r"R_2^2=1^2+3^2=10" in solution
    assert "По теореме Пифагора" in solution
    assert "18-10" in solution
    assert r"\frac{S}{\pi}=8" in solution
    assert "Поэтому" in solution
    assert solution.index("Поэтому") < solution.index(r"\frac{S}{\pi}=8")


def test_annulus_solution_diagram_preserves_ring_and_adds_two_red_triangles(
    tmp_path: Path,
) -> None:
    """Draw lattice-based Pythagorean constructions without floating labels."""

    prepared = _prepared_ring(tmp_path)
    strategy = get_solution_strategy("annulus-area")
    analysis = strategy.analyze(prepared, get_group_profile("245008"))

    rendered = strategy.render_solution_svg(prepared, analysis).decode("utf-8")

    assert rendered.count("<circle") == 2
    assert 'id="solution-construction"' in rendered
    assert 'stroke="#e22"' in rendered
    assert rendered.count("<line") == 6
    assert rendered.count('data-kind="radius"') == 2
    assert rendered.count('data-kind="pythagorean-leg"') == 4
    radius_lines = [
        fragment.split("/>", 1)[0]
        for fragment in rendered.split("<line")[1:]
        if 'data-kind="radius"' in fragment
    ]
    leg_lines = [
        fragment.split("/>", 1)[0]
        for fragment in rendered.split("<line")[1:]
        if 'data-kind="pythagorean-leg"' in fragment
    ]
    assert all("stroke-dasharray" not in line for line in radius_lines)
    assert all('stroke-dasharray="5 4"' in line for line in leg_lines)
    assert "R₁" not in rendered
    assert "R₂" not in rendered


def test_annulus_strategy_uses_direct_radii_without_degenerate_triangles(
    tmp_path: Path,
) -> None:
    """Use one radius segment and direct wording for perfect-square radii."""

    prepared = replace(
        _prepared_ring(tmp_path),
        outer_point=(7, 5),
        inner_point=(4, 5),
        outer_radius_squared=4,
        inner_radius_squared=1,
        converter_diagnostics={
            "svg_center": [100.0, 100.0],
            "svg_outer_radius": 40.0,
            "svg_inner_radius": 20.0,
            "grid_cell_size": 20.0,
        },
    )
    strategy = get_solution_strategy("annulus-area")
    profile = get_group_profile("245008")
    analysis = strategy.analyze(prepared, profile)

    solution = strategy.build_solution_html(analysis, profile)
    rendered = strategy.render_solution_svg(prepared, analysis).decode("utf-8")

    assert r"R_1^2=2^2=4" in solution
    assert r"R_2^2=1^2=1" in solution
    assert "По теореме Пифагора" not in solution
    assert rendered.count('data-kind="radius"') == 2
    assert 'data-kind="pythagorean-leg"' not in rendered
