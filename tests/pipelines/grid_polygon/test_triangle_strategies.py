"""Verify reusable triangle strategies against audited group-independent behavior."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from solution_runner.pipelines.grid_polygon.group_profiles import get_group_profile
from solution_runner.pipelines.grid_polygon.models import PreparedGridPolygon
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy
from solution_runner.pipelines.grid_polygon.strategies.protocol import format_number


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _characterization(strategy_key: str) -> dict[str, object]:
    """Load one minimized audited strategy fixture."""

    path = next(
        path
        for path in FIXTURE_DIR.glob("*triangle.json")
        if json.loads(path.read_text())["strategy_key"] == strategy_key
    )
    return json.loads(path.read_text())


def _condition_svg(coordinates: tuple[tuple[int, int], ...]) -> bytes:
    """Build a square-grid SVG whose visible polygon matches logical points."""

    width = (max(x for x, _ in coordinates) + 2) * 20
    height = (max(y for _, y in coordinates) + 2) * 20
    lines = []
    for x in range(0, width + 1, 20):
        lines.append(
            f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="#bfbfbf"/>'
        )
    for y in range(0, height + 1, 20):
        lines.append(
            f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="#bfbfbf"/>'
        )
    points = " ".join(f"{x * 20},{y * 20}" for x, y in coordinates)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
        + "".join(lines)
        + f'<polygon id="condition-polygon" points="{points}" fill="#8da3cc" '
        'stroke="#111"/>'
        + "</svg>"
    ).encode()


def _prepared(tmp_path: Path, fixture: dict[str, object]) -> PreparedGridPolygon:
    """Freeze one fixture SVG for a pure strategy invocation."""

    coordinates = tuple(tuple(point) for point in fixture["coordinates"])
    path = tmp_path / f'{fixture["strategy_key"]}.svg'
    path.write_bytes(_condition_svg(coordinates))
    return PreparedGridPolygon(
        problem_id=f'problem-{fixture["source_problem_id"]}',
        source_problem_id=str(fixture["source_problem_id"]),
        condition_asset_id="asset-condition",
        condition_svg_path=path,
        condition_svg_sha256="fixture-sha",
        coordinates=coordinates,
        vertex_count=3,
        condition_was_replaced=True,
        converter_diagnostics={},
    )


@pytest.mark.parametrize(
    "strategy_key",
    ["right-triangle", "base-height-triangle", "bounding-rectangle-triangle"],
)
def test_triangle_strategy_matches_characterization(
    tmp_path: Path,
    strategy_key: str,
) -> None:
    """Keep formulas and answers stable while removing group-named modules."""

    fixture = _characterization(strategy_key)
    profile = get_group_profile(str(fixture["group_key"]))
    strategy = get_solution_strategy(strategy_key)
    analysis = strategy.analyze(_prepared(tmp_path, fixture), profile)

    assert format_number(analysis.area) == fixture["expected"]["area"]
    assert strategy.build_formula(analysis, profile) == fixture["expected"]["formula"]
    assert strategy.build_answer_html(analysis) == fixture["expected"]["answer_html"]


def test_base_height_strategy_handles_both_base_orientations(tmp_path: Path) -> None:
    """Use the same implementation for vertical and horizontal bases."""

    strategy = get_solution_strategy("base-height-triangle")
    profile = get_group_profile("27545")
    vertical_fixture = _characterization("base-height-triangle")
    vertical = strategy.analyze(_prepared(tmp_path, vertical_fixture), profile)
    horizontal_fixture = dict(vertical_fixture)
    horizontal_fixture["coordinates"] = [[1, 2], [7, 2], [4, 6]]
    horizontal_fixture["source_problem_id"] = "horizontal"
    horizontal = strategy.analyze(_prepared(tmp_path, horizontal_fixture), profile)

    assert vertical.details["orientation"] == "vertical"
    assert horizontal.details["orientation"] == "horizontal"
    assert vertical.area == 4.5
    assert horizontal.area == 12


@pytest.mark.parametrize(
    "strategy_key",
    ["base-height-triangle", "bounding-rectangle-triangle"],
)
def test_triangle_overlay_preserves_condition_polygon(
    tmp_path: Path,
    strategy_key: str,
) -> None:
    """Add construction lines without rebuilding or shrinking the blue polygon."""

    fixture = _characterization(strategy_key)
    prepared = _prepared(tmp_path, fixture)
    profile = get_group_profile(str(fixture["group_key"]))
    strategy = get_solution_strategy(strategy_key)
    analysis = strategy.analyze(prepared, profile)
    before = ElementTree.fromstring(prepared.condition_svg_path.read_bytes())
    after_bytes = strategy.render_solution_svg(prepared, analysis)
    after = ElementTree.fromstring(after_bytes)
    before_polygon = next(element for element in before.iter() if element.tag.endswith("polygon"))
    after_polygon = next(element for element in after.iter() if element.tag.endswith("polygon"))

    assert after_polygon.get("points") == before_polygon.get("points")
    assert b'id="solution-construction"' in after_bytes
    assert after_bytes.count(b'data-kind="bounding-side"') in {0, 4}


def test_base_height_overlay_contains_red_geometry_and_right_angle(
    tmp_path: Path,
) -> None:
    """Render the reusable base, height, and perpendicular marker construction."""

    fixture = _characterization("base-height-triangle")
    prepared = _prepared(tmp_path, fixture)
    profile = get_group_profile("27545")
    strategy = get_solution_strategy("base-height-triangle")
    rendered = strategy.render_solution_svg(
        prepared,
        strategy.analyze(prepared, profile),
    )

    assert b'data-kind="base"' in rendered
    assert b'data-kind="height"' in rendered
    assert b'data-kind="right-angle-marker"' in rendered
    assert b'stroke="#e22"' in rendered


def test_base_height_overlay_maps_a_separate_line_outline(tmp_path: Path) -> None:
    """Catch solution rendering that supports polygon tags but not source line loops."""

    coordinates = ((1, 5), (3, 1), (8, 5))
    grid = "".join(
        f'<line x1="{value}" y1="0" x2="{value}" y2="160" stroke="#ADAAAA"/>'
        f'<line x1="0" y1="{value}" x2="200" y2="{value}" stroke="#ADAAAA"/>'
        for value in range(0, 201, 20)
    )
    outline = "".join(
        f'<line x1="{start[0] * 20}" y1="{start[1] * 20}" '
        f'x2="{end[0] * 20}" y2="{end[1] * 20}" stroke="#000000"/>'
        for start, end in zip(coordinates, coordinates[1:] + coordinates[:1])
    )
    path = tmp_path / "line-triangle.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 160">'
        f"{grid}{outline}</svg>"
    )
    prepared = PreparedGridPolygon(
        problem_id="problem-line-triangle",
        source_problem_id="line-triangle",
        condition_asset_id="asset-condition",
        condition_svg_path=path,
        condition_svg_sha256="fixture-sha",
        coordinates=coordinates,
        vertex_count=3,
        condition_was_replaced=False,
        converter_diagnostics={},
    )
    strategy = get_solution_strategy("base-height-triangle")
    analysis = strategy.analyze(prepared, get_group_profile("348403"))

    rendered = strategy.render_solution_svg(prepared, analysis)

    assert rendered.count(b'id="solution-construction"') == 1
    assert b'data-kind="height"' in rendered


def test_right_triangle_strategy_does_not_require_solution_diagram(tmp_path: Path) -> None:
    """Retain the prototype behavior that writes text and answer only."""

    fixture = _characterization("right-triangle")
    prepared = _prepared(tmp_path, fixture)
    strategy = get_solution_strategy("right-triangle")

    assert strategy.requires_solution_diagram is False
    assert strategy.render_solution_svg(
        prepared,
        strategy.analyze(prepared, get_group_profile("27543")),
    ) == prepared.condition_svg_path.read_bytes()


@pytest.mark.parametrize(
    ("source_problem_id", "coordinates", "expected_area", "expected_formula"),
    [
        (
            "244982",
            ((1, 2), (3, 1), (2, 4)),
            "2,5",
            r"S=2\cdot 3-\frac{1}{2}\cdot 1\cdot 3"
            r"-\frac{1}{2}\cdot 2\cdot 1-\frac{1}{2}\cdot 1\cdot 2=2{,}5",
        ),
        (
            "252219",
            ((3, 2), (4, 3), (1, 4)),
            "2",
            r"S=3\cdot 2-\frac{1}{2}\cdot 2\cdot 2"
            r"-\frac{1}{2}\cdot 3\cdot 1-\frac{1}{2}\cdot 1\cdot 1=2",
        ),
        (
            "252247",
            ((5, 2), (1, 5), (3, 6)),
            "5",
            r"S=4\cdot 4-\frac{1}{2}\cdot 4\cdot 3"
            r"-\frac{1}{2}\cdot 2\cdot 4-\frac{1}{2}\cdot 2\cdot 1=5",
        ),
    ],
)
def test_group_244982_bounding_rectangle_canaries(
    tmp_path: Path,
    source_problem_id: str,
    coordinates: tuple[tuple[int, int], ...],
    expected_area: str,
    expected_formula: str,
) -> None:
    """Keep the prototype and two audited PNG triangles on the shared engine."""

    fixture = {
        "strategy_key": "bounding-rectangle-triangle",
        "source_problem_id": source_problem_id,
        "coordinates": coordinates,
    }
    prepared = _prepared(tmp_path, fixture)
    profile = get_group_profile("244982")
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    rendered = strategy.render_solution_svg(prepared, analysis)

    assert analysis.area == analysis.area_by_coordinates
    assert format_number(analysis.area) == expected_area
    assert strategy.build_formula(analysis, profile) == expected_formula
    assert rendered.count(b'data-kind="bounding-side"') == 4
