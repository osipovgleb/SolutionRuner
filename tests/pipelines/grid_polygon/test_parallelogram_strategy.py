"""Verify reusable three-method parallelogram solutions and diagrams."""

from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import PreparedGridPolygon
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy


def _svg(coordinates: tuple[tuple[int, int], ...]) -> bytes:
    """Build one deterministic grid SVG whose polygon follows logical points."""

    width = (max(x for x, _ in coordinates) + 2) * 20
    height = (max(y for _, y in coordinates) + 2) * 20
    points = " ".join(f"{x * 20},{y * 20}" for x, y in coordinates)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
        f'<polygon id="condition-polygon" points="{points}" '
        'fill="#8da3cc" stroke="#111"/>'
        "</svg>"
    ).encode()


def _prepared(
    tmp_path: Path,
    source_problem_id: str,
    coordinates: tuple[tuple[int, int], ...],
) -> PreparedGridPolygon:
    """Freeze one audited parallelogram without any transport dependency."""

    path = tmp_path / f"{source_problem_id}.svg"
    path.write_bytes(_svg(coordinates))
    return PreparedGridPolygon(
        problem_id=f"problem-{source_problem_id}",
        source_problem_id=source_problem_id,
        condition_asset_id=f"condition-{source_problem_id}",
        condition_svg_path=path,
        condition_svg_sha256="fixture",
        coordinates=coordinates,
        vertex_count=4,
        condition_was_replaced=False,
        converter_diagnostics={},
    )


@pytest.mark.parametrize(
    ("source_problem_id", "coordinates", "base", "height", "area"),
    [
        ("348499", ((1, 4), (4, 1), (10, 1), (7, 4)), 6, 3, 18),
        ("401035", ((1, 5), (4, 1), (9, 1), (6, 5)), 5, 4, 20),
        ("402793", ((1, 7), (2, 1), (9, 1), (8, 7)), 7, 6, 42),
        ("404285", ((1, 8), (3, 1), (6, 1), (4, 8)), 3, 7, 21),
        ("vertical", ((4, 1), (1, 4), (1, 10), (4, 7)), 6, 3, 18),
    ],
)
def test_parallelogram_area_agrees_by_height_rectangle_pick_and_coordinates(
    tmp_path: Path,
    source_problem_id: str,
    coordinates: tuple[tuple[int, int], ...],
    base: int,
    height: int,
    area: int,
) -> None:
    """Reject a result whenever any independently derived area can drift."""

    profile = get_group_profile("348499")
    strategy = get_solution_strategy(profile.strategy_key)
    analysis = strategy.analyze(
        _prepared(tmp_path, source_problem_id, coordinates),
        profile,
    )

    assert analysis.area == analysis.area_by_coordinates == area
    assert analysis.details["base_length"] == base
    assert analysis.details["height"] == height
    assert analysis.details["base_height_area"] == area
    assert analysis.details["rectangle_area"] == area
    assert analysis.details["pick_area"] == area


def test_parent_builds_three_ordered_solutions_and_matching_diagrams(
    tmp_path: Path,
) -> None:
    """Keep each diagram inside its matching base, rectangle, or Pick method."""

    coordinates = ((1, 4), (4, 1), (10, 1), (7, 4))
    prepared = _prepared(tmp_path, "348499", coordinates)
    profile = get_group_profile("348499")
    strategy = get_solution_strategy(profile.strategy_key)
    analysis = strategy.analyze(prepared, profile)
    solution = strategy.build_solution_html(analysis, profile)
    diagrams = strategy.render_solution_diagrams(prepared, analysis, profile)

    assert solution.count('data-content-kind="solution"') == 3
    assert r"S=ah=6\cdot 3=18" in solution
    assert (
        r"S=9\cdot 3-\frac{1}{2}\cdot 3\cdot 3"
        r"-\frac{1}{2}\cdot 3\cdot 3=18"
    ) in solution
    assert "По формуле Пика" in solution
    assert (
        r"S=\mathrm{В}+\frac{\mathrm{Г}}{2}-1="
        r"10+\frac{18}{2}-1=18"
    ) in solution
    assert [diagram.asset_key for diagram in diagrams] == [
        "generated_solution_diagram",
        "generated_rectangle_diagram",
        "generated_pick_diagram",
    ]
    assert [diagram.solution_variant_index for diagram in diagrams] == [0, 1, 2]
    assert b'data-kind="base"' in diagrams[0].svg_bytes
    assert b'data-kind="height"' in diagrams[0].svg_bytes
    assert diagrams[1].svg_bytes.count(b'data-kind="bounding-side"') == 4
    assert b'data-kind="pick-interior"' in diagrams[2].svg_bytes
    assert b'fill="#F5C518"' in diagrams[2].svg_bytes
    assert b'data-kind="pick-boundary"' in diagrams[2].svg_bytes
    assert b'fill="#22A06B"' in diagrams[2].svg_bytes

    expected_points = ElementTree.fromstring(prepared.condition_svg_path.read_bytes())
    expected_polygon = next(
        element for element in expected_points.iter() if element.tag.endswith("polygon")
    ).get("points")
    for diagram in diagrams:
        rendered = ElementTree.fromstring(diagram.svg_bytes)
        polygon = next(
            element for element in rendered.iter() if element.tag.endswith("polygon")
        )
        assert polygon.get("points") == expected_polygon


def test_non_parallelogram_is_rejected_before_solution_rendering(tmp_path: Path) -> None:
    """Never present the base-height rule for a generic four-point polygon."""

    profile = get_group_profile("348499")
    strategy = get_solution_strategy(profile.strategy_key)
    prepared = _prepared(
        tmp_path,
        "not-parallelogram",
        ((1, 4), (4, 1), (10, 1), (8, 4)),
    )

    with pytest.raises(ValueError, match="parallelogram"):
        strategy.analyze(prepared, profile)
