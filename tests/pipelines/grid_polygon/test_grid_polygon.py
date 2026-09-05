"""Protect canonical SVG grid extraction and coordinate metadata handling."""

from __future__ import annotations

from pathlib import Path

import pytest

from solution_runner.pipelines.grid_polygon.geometry.grid_polygon import (
    GridPolygonError,
    ordered_coordinates_from_svg,
    parse_coordinate_alt,
    parse_grid_polygon,
    polygon_sha256,
    serialize_coordinate_alt,
)


FIXTURE_DIR = Path(__file__).with_name("fixtures")


def _grid_svg(polygon: str) -> bytes:
    """Return one compact square-grid SVG with the requested polygon traversal."""

    lines = "".join(
        f'<line x1="{value}" y1="0" x2="{value}" y2="220" stroke="#ADAAAA"/>'
        f'<line x1="0" y1="{value}" x2="220" y2="{value}" stroke="#ADAAAA"/>'
        for value in range(0, 221, 20)
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">'
        f"{lines}<polygon points=\"{polygon}\" fill=\"#8da3cc\" stroke=\"#111\"/>"
        "</svg>"
    ).encode()


def _line_grid_svg(coordinates: tuple[tuple[int, int], ...]) -> bytes:
    """Return a square-grid SVG whose outline is stored as separate black lines."""

    grid = "".join(
        f'<line x1="{value}" y1="0" x2="{value}" y2="220" stroke="#ADAAAA"/>'
        f'<line x1="0" y1="{value}" x2="220" y2="{value}" stroke="#ADAAAA"/>'
        for value in range(0, 221, 20)
    )
    outline = "".join(
        f'<line x1="{start[0] * 20}" y1="{start[1] * 20}" '
        f'x2="{end[0] * 20}" y2="{end[1] * 20}" stroke="#000000"/>'
        for start, end in zip(coordinates, coordinates[1:] + coordinates[:1])
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">'
        f"{grid}{outline}</svg>"
    ).encode()


def test_svg_recovers_edge_order_from_display_sorted_coordinates() -> None:
    """Keep canonical alt order separate from the visible polygon traversal."""

    canonical = ((3, 2), (1, 6), (8, 6), (3, 9))

    ordered = ordered_coordinates_from_svg(
        _grid_svg("80,40 180,100 80,180 40,100"),
        canonical,
    )

    assert ordered == ((3, 1), (8, 4), (3, 8), (1, 4))
    assert set(ordered) != set(canonical)


def test_parser_removes_bounded_collinear_intermediate_vertex() -> None:
    """Catch selecting a service polygon or preserving a point on one edge."""

    parsed = parse_grid_polygon(
        (FIXTURE_DIR / "legacy_intermediate_vertex.svg").read_bytes(),
        expected_vertices=3,
        geometry_profile="base-height-triangle",
    )

    assert parsed.coordinates == ((3, 1), (1, 10), (3, 7))
    assert parsed.discarded_intermediate_points == 1
    assert parsed.grid_step_x == pytest.approx(20)
    assert parsed.grid_step_y == pytest.approx(20)


def test_parser_does_not_collapse_genuine_quadrilateral() -> None:
    """Catch over-eager triangle cleanup deleting a real fourth vertex."""

    parsed = parse_grid_polygon(
        (FIXTURE_DIR / "genuine_quadrilateral.svg").read_bytes(),
        expected_vertices=4,
        geometry_profile="parallel-bases-trapezoid",
    )

    assert parsed.coordinates == ((1, 1), (1, 5), (5, 4), (5, 2))
    assert parsed.discarded_intermediate_points == 0


def test_coordinate_alt_has_one_canonical_round_trip() -> None:
    """Catch divergent alt formatting or acceptance of ambiguous structures."""

    coordinates = ((8, 2), (1, 4), (1, 8))
    serialized = serialize_coordinate_alt(coordinates)

    assert serialized == "[(8,2), (1,4), (1,8)]"
    assert parse_coordinate_alt(serialized, expected_vertices=3) == coordinates
    with pytest.raises(GridPolygonError, match="distinct"):
        parse_coordinate_alt("[(1,2), (1,2), (3,4)]", expected_vertices=3)


def test_polygon_digest_is_stable_and_coordinates_must_be_near_grid() -> None:
    """Catch unstable hashing or silent snapping of a visibly displaced vertex."""

    svg = (FIXTURE_DIR / "genuine_quadrilateral.svg").read_bytes()
    assert polygon_sha256(svg) == polygon_sha256(svg)
    displaced = svg.replace(b"21,21", b"30,21")
    with pytest.raises(GridPolygonError, match="x-coordinate"):
        parse_grid_polygon(
            displaced,
            expected_vertices=4,
            geometry_profile="parallel-bases-trapezoid",
        )


@pytest.mark.parametrize(
    ("coordinates", "expected_vertices", "geometry_profile"),
    [
        (((1, 5), (3, 1), (8, 5)), 3, "base-height-triangle"),
        (((1, 3), (4, 1), (6, 1), (6, 6)), 4, "bounding-rectangle-quadrilateral"),
        (((1, 4), (4, 1), (10, 1), (7, 4)), 4, "parallelogram-three-methods"),
    ],
)
def test_parser_recovers_fixed_polygon_from_separate_outline_lines(
    coordinates: tuple[tuple[int, int], ...],
    expected_vertices: int,
    geometry_profile: str,
) -> None:
    """Catch rejecting source SVGs that encode a valid outline without polygon tags."""

    parsed = parse_grid_polygon(
        _line_grid_svg(coordinates),
        expected_vertices=expected_vertices,
        geometry_profile=geometry_profile,
    )

    assert parsed.coordinates == coordinates
    assert parsed.raw_polygon_points == tuple(
        (float(x * 20), float(y * 20)) for x, y in coordinates
    )


def test_parser_recovers_variable_vertex_cell_figure_from_outline_lines() -> None:
    """Catch forcing every axis-aligned cell figure into a fixed vertex count."""

    coordinates = (
        (1, 1),
        (4, 1),
        (4, 2),
        (3, 2),
        (3, 4),
        (5, 4),
        (5, 5),
        (1, 5),
    )

    parsed = parse_grid_polygon(
        _line_grid_svg(coordinates),
        expected_vertices=None,
        geometry_profile="grid-cell-count",
    )

    assert parsed.coordinates == (
        (1, 1),
        (1, 5),
        (5, 5),
        (5, 4),
        (3, 4),
        (3, 2),
        (4, 2),
        (4, 1),
    )


def test_parser_joins_sampled_open_polylines_into_one_triangle() -> None:
    """Recover a triangle whose three sides are separately sampled polylines."""

    grid = "".join(
        f'<line x1="{value}" y1="0" x2="{value}" y2="120" stroke="#ADAAAA"/>'
        f'<line x1="0" y1="{value}" x2="120" y2="{value}" stroke="#ADAAAA"/>'
        for value in range(0, 121, 20)
    )
    outline = (
        '<polyline points="20,80 26,74 31,69 80,20" stroke="#000" fill="none"/>'
        '<polyline points="80,20 87,40 100,80" stroke="#000" fill="none"/>'
        '<polyline points="100,80 65,80 20,80" stroke="#000" fill="none"/>'
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120">'
        f"{grid}{outline}</svg>"
    ).encode()

    parsed = parse_grid_polygon(
        svg,
        expected_vertices=3,
        geometry_profile="base-height-triangle",
    )

    assert parsed.coordinates == ((1, 4), (4, 1), (5, 4))
