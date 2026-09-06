"""Verify reusable trapezoid strategies and shared solution rendering."""

from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
from xml.etree import ElementTree

import pytest

from solution_runner.pipelines.core.group_profiles import get_group_profile
from solution_runner.pipelines.core.models import PreparedGridPolygon
from solution_runner.pipelines.grid_polygon.strategies import get_solution_strategy
from solution_runner.pipelines.grid_polygon.strategies.protocol import format_number


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _fixture(key: str) -> dict[str, object]:
    """Load one audited trapezoid characterization."""

    return next(
        json.loads(path.read_text())
        for path in FIXTURE_DIR.glob("*trapezoid.json")
        if json.loads(path.read_text())["strategy_key"] == key
    )


def _svg(coordinates: tuple[tuple[int, int], ...]) -> bytes:
    """Build one minimal square-grid condition SVG."""

    width = (max(x for x, _ in coordinates) + 2) * 20
    height = (max(y for _, y in coordinates) + 2) * 20
    grid = [
        *(f'<line x1="{x}" y1="0" x2="{x}" y2="{height}" stroke="#bfbfbf"/>' for x in range(0, width + 1, 20)),
        *(f'<line x1="0" y1="{y}" x2="{width}" y2="{y}" stroke="#bfbfbf"/>' for y in range(0, height + 1, 20)),
    ]
    points = " ".join(f"{x * 20},{y * 20}" for x, y in coordinates)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">'
        + "".join(grid)
        + f'<polygon id="condition-polygon" points="{points}" fill="#8da3cc" stroke="#111"/>'
        + "</svg>"
    ).encode()


def _prepared(tmp_path: Path, fixture: dict[str, object]) -> PreparedGridPolygon:
    """Create one frozen prepared record for strategy-only tests."""

    coordinates = tuple(tuple(point) for point in fixture["coordinates"])
    path = tmp_path / f'{fixture["strategy_key"]}.svg'
    path.write_bytes(_svg(coordinates))
    return PreparedGridPolygon(
        problem_id=f'problem-{fixture["source_problem_id"]}',
        source_problem_id=str(fixture["source_problem_id"]),
        condition_asset_id="condition-asset",
        condition_svg_path=path,
        condition_svg_sha256="fixture",
        coordinates=coordinates,
        vertex_count=4,
        condition_was_replaced=True,
        converter_diagnostics={},
    )


@pytest.mark.parametrize(
    "strategy_key",
    ["parallel-bases-trapezoid", "bounding-rectangle-trapezoid"],
)
def test_trapezoid_strategy_matches_characterization(
    tmp_path: Path,
    strategy_key: str,
) -> None:
    """Keep exact audited area, formula, and answer behavior."""

    fixture = _fixture(strategy_key)
    profile = get_group_profile(str(fixture["group_key"]))
    prepared = _prepared(tmp_path, fixture)
    strategy = get_solution_strategy(strategy_key)
    analysis = strategy.analyze(prepared, profile)

    assert format_number(analysis.area) == fixture["expected"]["area"]
    assert strategy.build_formula(analysis, profile) == fixture["expected"]["formula"]
    assert strategy.build_answer_html(analysis) == fixture["expected"]["answer_html"]


def test_parallel_bases_strategy_is_orientation_independent(tmp_path: Path) -> None:
    """Use one base-height implementation for horizontal and vertical bases."""

    fixture = _fixture("parallel-bases-trapezoid")
    strategy = get_solution_strategy("parallel-bases-trapezoid")
    profile = get_group_profile("27557")
    vertical = strategy.analyze(_prepared(tmp_path, fixture), profile)
    horizontal_fixture = dict(fixture)
    horizontal_fixture["coordinates"] = [[2, 1], [9, 1], [8, 9], [4, 9]]
    horizontal_fixture["source_problem_id"] = "horizontal"
    horizontal = strategy.analyze(_prepared(tmp_path, horizontal_fixture), profile)

    assert vertical.area == horizontal.area == 44
    assert vertical.details["orientation"] == "vertical"
    assert horizontal.details["orientation"] == "horizontal"


def test_bounding_trapezoid_draws_complete_rectangle_without_changing_polygon(
    tmp_path: Path,
) -> None:
    """Protect the missing upper-left horizontal bounding-side regression."""

    fixture = _fixture("bounding-rectangle-trapezoid")
    profile = get_group_profile("244986")
    prepared = _prepared(tmp_path, fixture)
    strategy = get_solution_strategy("bounding-rectangle-trapezoid")
    before = ElementTree.fromstring(prepared.condition_svg_path.read_bytes())
    rendered = strategy.render_solution_svg(
        prepared,
        strategy.analyze(prepared, profile),
    )
    after = ElementTree.fromstring(rendered)
    before_polygon = next(element for element in before.iter() if element.tag.endswith("polygon"))
    after_polygon = next(element for element in after.iter() if element.tag.endswith("polygon"))

    assert rendered.count(b'data-kind="bounding-side"') == 4
    assert after_polygon.get("points") == before_polygon.get("points")
    assert b'id="solution-construction"' in rendered


@pytest.mark.parametrize(
    ("source_problem_id", "coordinates", "expected_area", "expected_formula"),
    [
        (
            "244983",
            ((2, 2), (4, 1), (3, 3), (1, 4)),
            "3",
            r"S=3\cdot 3-1\cdot 1-1\cdot 1"
            r"-\frac{1}{2}\cdot 2\cdot 1-\frac{1}{2}\cdot 2\cdot 1"
            r"-\frac{1}{2}\cdot 1\cdot 2-\frac{1}{2}\cdot 1\cdot 2=3",
        ),
        (
            "252631",
            ((7, 2), (3, 4), (5, 6), (1, 8)),
            "12",
            r"S=6\cdot 6-2\cdot 2-2\cdot 2"
            r"-\frac{1}{2}\cdot 4\cdot 2-\frac{1}{2}\cdot 4\cdot 2"
            r"-\frac{1}{2}\cdot 2\cdot 4-\frac{1}{2}\cdot 2\cdot 4=12",
        ),
    ],
)
def test_rhombus_bounding_rectangle_canaries(
    tmp_path: Path,
    source_problem_id: str,
    coordinates: tuple[tuple[int, int], ...],
    expected_area: str,
    expected_formula: str,
) -> None:
    """Keep two audited rhombi on the shared rectangle-complement engine."""

    fixture = {
        "strategy_key": "bounding-rectangle-quadrilateral",
        "source_problem_id": source_problem_id,
        "coordinates": coordinates,
    }
    prepared = _prepared(tmp_path, fixture)
    profile = get_group_profile("244983")
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    rendered = strategy.render_solution_svg(prepared, analysis)

    assert analysis.area == analysis.area_by_coordinates
    assert format_number(analysis.area) == expected_area
    assert strategy.build_formula(analysis, profile) == expected_formula
    assert rendered.count(b'data-kind="bounding-side"') == 4
    assert "Площадь четырёхугольника" in strategy.build_solution_html(
        analysis,
        profile,
    )


@pytest.mark.parametrize(
    (
        "source_problem_id",
        "coordinates",
        "expected_area",
        "expected_rectangle_formula",
        "expected_diagonal_formula",
    ),
    [
        (
            "27553",
            ((4, 5), (1, 3), (4, 1), (7, 3)),
            "12",
            r"S=6\cdot 4-4\cdot \frac{1}{2}\cdot 3\cdot 2=12",
            r"S=\frac{1}{2}\cdot 6\cdot 4=12",
        ),
        (
            "5313",
            ((5, 7), (1, 4), (5, 1), (9, 4)),
            "24",
            r"S=8\cdot 6-4\cdot \frac{1}{2}\cdot 4\cdot 3=24",
            r"S=\frac{1}{2}\cdot 8\cdot 6=24",
        ),
        (
            "248875",
            ((3, 1), (5, 2), (3, 3), (1, 2)),
            "4",
            r"S=4\cdot 2-4\cdot \frac{1}{2}\cdot 2\cdot 1=4",
            r"S=\frac{1}{2}\cdot 4\cdot 2=4",
        ),
    ],
)
def test_group_27553_builds_parent_style_two_method_solutions(
    tmp_path: Path,
    source_problem_id: str,
    coordinates: tuple[tuple[int, int], ...],
    expected_area: str,
    expected_rectangle_formula: str,
    expected_diagonal_formula: str,
) -> None:
    """Catch loss of either independently verified parent solution method."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": source_problem_id,
            "coordinates": coordinates,
        },
    )
    profile = get_group_profile("27553")
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    solution_html = strategy.build_solution_html(analysis, profile)

    assert format_number(analysis.area) == expected_area
    assert strategy.build_formula(analysis, profile) == expected_rectangle_formula
    assert solution_html.count('data-content-kind="solution"') == 2
    assert 'data-solution-title="Решение"' in solution_html
    assert 'data-solution-title="Приведем другое решение."' in solution_html
    assert expected_rectangle_formula in solution_html
    assert expected_diagonal_formula in solution_html


def test_group_27553_rejects_a_non_rhombus_before_rendering(tmp_path: Path) -> None:
    """Prevent the diagonal method from being applied from condition prose alone."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": "not-a-rhombus",
            "coordinates": ((1, 1), (4, 1), (3, 3), (1, 4)),
        },
    )
    profile = get_group_profile("27553")
    strategy = get_solution_strategy(profile.strategy_key)

    with pytest.raises(ValueError, match="four equal sides"):
        strategy.analyze(prepared, profile)


def _pick_quadrilateral_profile():
    """Return the shared arbitrary-quadrilateral profile before registry rollout."""

    return replace(
        get_group_profile("27553"),
        group_key="canary",
        solution_text_profile="quadrilateral-pick",
    )


def test_concave_monotone_quadrilateral_uses_one_rectangle_and_pick(
    tmp_path: Path,
) -> None:
    """Render the 27555 parent with one rectangle and a child-visible Pick method."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": "27555",
            "coordinates": ((4, 1), (7, 5), (4, 3), (1, 5)),
        },
    )
    profile = _pick_quadrilateral_profile()
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    solution_html = strategy.build_solution_html(analysis, profile)
    rendered = strategy.render_solution_svg(prepared, analysis)

    assert analysis.area == 6
    assert analysis.details["construction_mode"] == "rectangle-complement"
    assert analysis.details["pick_interior"] == 5
    assert analysis.details["pick_boundary"] == 4
    assert strategy.build_formula(analysis, profile) == (
        r"S=6\cdot 4"
        r"-\frac{1}{2}\cdot 3\cdot 4"
        r"-\frac{1}{2}\cdot 3\cdot 4"
        r"-\frac{1}{2}\cdot 3\cdot 2"
        r"-\frac{1}{2}\cdot 3\cdot 2=6"
    )
    assert solution_html.count('data-content-kind="solution"') == 2
    assert (
        r"S=\mathrm{В}+\frac{\mathrm{Г}}{2}-1="
        r"5+\frac{4}{2}-1=6"
    ) in solution_html
    assert rendered.count(b'data-kind="bounding-side"') == 4


def test_rectangle_complement_redraws_the_polygon_edge_that_closes_a_rectangle(
    tmp_path: Path,
) -> None:
    """Keep a pure exterior rectangle visibly closed on all four red sides."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": "244997",
            "coordinates": ((2, 3), (1, 1), (4, 2), (2, 2)),
        },
    )
    profile = _pick_quadrilateral_profile()
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    rendered = strategy.render_solution_svg(prepared, analysis)

    assert analysis.details["exterior_terms"][0] == (
        "rectangle",
        2,
        1,
        2,
    )
    assert rendered.count(b'data-kind="decomposition"') == 1


def test_pick_profile_renders_separate_coloured_lattice_diagram(
    tmp_path: Path,
) -> None:
    """Keep the rectangle and Pick illustrations separate and count-identical."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": "27554",
            "coordinates": ((3, 6), (1, 3), (4, 1), (6, 3)),
        },
    )
    profile = _pick_quadrilateral_profile()
    strategy = get_solution_strategy(profile.strategy_key)
    analysis = strategy.analyze(prepared, profile)

    diagrams = strategy.render_solution_diagrams(prepared, analysis, profile)

    assert [(item.asset_key, item.solution_variant_index) for item in diagrams] == [
        ("generated_solution_diagram", 0),
        ("generated_pick_diagram", 1),
    ]
    pick_root = ElementTree.fromstring(diagrams[1].svg_bytes)
    interior = [node for node in pick_root.iter() if node.get("data-kind") == "pick-interior"]
    boundary = [node for node in pick_root.iter() if node.get("data-kind") == "pick-boundary"]
    assert len(interior) == analysis.details["pick_interior"]
    assert len(boundary) == analysis.details["pick_boundary"]
    assert {node.get("fill") for node in interior} == {"#F5C518"}
    assert {node.get("fill") for node in boundary} == {"#22A06B"}
    assert b'id="solution-construction"' not in diagrams[1].svg_bytes


def test_group_323790_places_pick_before_rectangle_solution(tmp_path: Path) -> None:
    """Match the OGE parent order without changing the shared two-method engine."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": "323791",
            "coordinates": ((1, 1), (5, 2), (4, 5), (1, 4)),
        },
    )
    profile = get_group_profile("323790")
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    solution_html = strategy.build_solution_html(analysis, profile)
    diagrams = strategy.render_solution_diagrams(prepared, analysis, profile)

    first_section, second_section = solution_html.split(
        '<section data-content-kind="solution"',
    )[1:]
    assert "По формуле Пика" in first_section
    assert "Площадь четырёхугольника" in second_section
    assert [(item.asset_key, item.solution_variant_index) for item in diagrams] == [
        ("generated_pick_diagram", 0),
        ("generated_solution_diagram", 1),
    ]


@pytest.mark.parametrize(
    ("source_problem_id", "coordinates", "expected_area"),
    [
        ("323750", ((1, 1), (1, 7), (7, 2), (6, 1)), "20,5"),
        ("323751", ((1, 7), (1, 1), (6, 1), (7, 3)), "23"),
        ("323769", ((1, 1), (1, 6), (6, 4), (4, 1)), "17"),
    ],
)
def test_group_323750_uses_pick_then_rectangle_for_audited_canaries(
    tmp_path: Path,
    source_problem_id: str,
    coordinates: tuple[tuple[int, int], ...],
    expected_area: str,
) -> None:
    """Protect the parent-compatible two-method flow across the group range."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": source_problem_id,
            "coordinates": coordinates,
        },
    )
    profile = get_group_profile("323750")
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    solution_html = strategy.build_solution_html(analysis, profile)
    diagrams = strategy.render_solution_diagrams(prepared, analysis, profile)

    assert format_number(analysis.area) == expected_area
    assert analysis.area == analysis.area_by_coordinates
    assert solution_html.index("По формуле Пика") < solution_html.index(
        "Площадь четырёхугольника"
    )
    assert [(item.asset_key, item.solution_variant_index) for item in diagrams] == [
        ("generated_pick_diagram", 0),
        ("generated_solution_diagram", 1),
    ]


def test_non_monotone_concave_quadrilateral_has_safe_triangle_fallback(
    tmp_path: Path,
) -> None:
    """Keep the 245000 parent solvable without inventing a false rectangle partition."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": "245000",
            "coordinates": ((3, 4), (1, 1), (4, 3), (2, 2)),
        },
    )
    profile = _pick_quadrilateral_profile()
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    solution_html = strategy.build_solution_html(analysis, profile)
    rendered = strategy.render_solution_svg(prepared, analysis)

    assert analysis.area == 1
    assert analysis.details["construction_mode"] == "outer-triangle-minus-notch"
    assert analysis.details["pick_interior"] == 0
    assert analysis.details["pick_boundary"] == 4
    assert solution_html.count('data-content-kind="solution"') == 2
    assert (
        r"S=\mathrm{В}+\frac{\mathrm{Г}}{2}-1="
        r"0+\frac{4}{2}-1=1"
    ) in solution_html
    assert b'data-kind="notch-side"' in rendered


@pytest.mark.parametrize(
    ("source_problem_id", "coordinates", "area", "interior", "boundary", "mode"),
    [
        ("27554", ((3, 6), (1, 3), (4, 1), (6, 3)), "12,5", 10, 7, "rectangle-complement"),
        ("27555", ((4, 1), (7, 5), (4, 3), (1, 5)), "6", 5, 4, "rectangle-complement"),
        ("244987", ((1, 3), (1, 2), (3, 1), (2, 3)), "2", 1, 4, "rectangle-complement"),
        ("244988", ((1, 3), (1, 2), (2, 1), (3, 3)), "2,5", 1, 5, "rectangle-complement"),
        ("244989", ((2, 3), (1, 2), (1, 1), (4, 3)), "2,5", 1, 5, "rectangle-complement"),
        ("244990", ((1, 4), (2, 2), (3, 1), (4, 4)), "5", 3, 6, "rectangle-complement"),
        ("244991", ((4, 2), (1, 1), (1, 4), (3, 3)), "5", 3, 6, "rectangle-complement"),
        ("244992", ((1, 3), (2, 1), (3, 3), (2, 4)), "3", 2, 4, "rectangle-complement"),
        ("244993", ((5, 5), (3, 2), (1, 1), (2, 3)), "4", 3, 4, "rectangle-complement"),
        ("244994", ((2, 2), (5, 1), (3, 4), (1, 3)), "5", 4, 4, "rectangle-complement"),
        ("244995", ((1, 1), (4, 1), (2, 2), (1, 4)), "3", 0, 8, "rectangle-complement"),
        ("244996", ((1, 1), (3, 2), (2, 2), (2, 3)), "1", 0, 4, "rectangle-complement"),
        ("244997", ((2, 3), (1, 1), (4, 2), (2, 2)), "1,5", 0, 5, "rectangle-complement"),
        ("244998", ((1, 3), (1, 1), (4, 1), (2, 2)), "2,5", 0, 7, "rectangle-complement"),
        ("244999", ((1, 3), (4, 1), (4, 2), (3, 2)), "1", 0, 4, "rectangle-complement"),
        ("245000", ((3, 4), (1, 1), (4, 3), (2, 2)), "1", 0, 4, "outer-triangle-minus-notch"),
        ("245001", ((1, 4), (2, 1), (4, 4), (2, 3)), "3", 2, 4, "rectangle-complement"),
        ("245002", ((1, 4), (3, 1), (4, 4), (2, 3)), "3", 2, 4, "rectangle-complement"),
        ("245003", ((3, 4), (2, 1), (1, 3), (2, 2)), "1", 0, 4, "rectangle-complement"),
        ("245004", ((1, 4), (1, 1), (3, 2), (2, 2)), "2", 0, 6, "rectangle-complement"),
        ("245006", ((3, 3), (2, 2), (1, 2), (2, 1)), "1", 0, 4, "rectangle-complement"),
        ("245007", ((4, 5), (1, 2), (5, 1), (3, 3)), "4,5", 2, 7, "rectangle-complement"),
    ],
)
def test_all_remaining_parent_quadrilaterals_have_two_exact_methods(
    tmp_path: Path,
    source_problem_id: str,
    coordinates: tuple[tuple[int, int], ...],
    area: str,
    interior: int,
    boundary: int,
    mode: str,
) -> None:
    """Protect every audited parent before its exact group profile is enabled."""

    prepared = _prepared(
        tmp_path,
        {
            "strategy_key": "bounding-rectangle-quadrilateral",
            "source_problem_id": source_problem_id,
            "coordinates": coordinates,
        },
    )
    profile = _pick_quadrilateral_profile()
    strategy = get_solution_strategy(profile.strategy_key)

    analysis = strategy.analyze(prepared, profile)
    solution_html = strategy.build_solution_html(analysis, profile)

    assert format_number(analysis.area) == area
    assert analysis.details["construction_mode"] == mode
    assert analysis.details["pick_interior"] == interior
    assert analysis.details["pick_boundary"] == boundary
    assert solution_html.count('data-content-kind="solution"') == 2
    assert "формуле Пика" in solution_html
