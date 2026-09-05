"""Protect reusable parallel-base trapezoid analysis across orientations."""

from __future__ import annotations

from fractions import Fraction

import pytest

from solution_runner.pipelines.grid_polygon.geometry import quadrilateral as quadrilateral_geometry
from solution_runner.pipelines.grid_polygon.geometry.quadrilateral import (
    analyze_parallel_bases_trapezoid,
    enumerate_lattice_points,
    quadrilateral_coordinate_area,
)


@pytest.mark.parametrize(
    ("coordinates", "base_lengths", "height", "area"),
    [
        (((1, 2), (1, 9), (9, 8), (9, 4)), (7, 4), 8, Fraction(44)),
        (((1, 2), (10, 2), (6, 7), (2, 7)), (9, 4), 5, Fraction(65, 2)),
    ],
)
def test_parallel_bases_support_vertical_and_horizontal_orientation(
    coordinates: tuple[tuple[int, int], ...],
    base_lengths: tuple[int, int],
    height: int,
    area: Fraction,
) -> None:
    """Catch orientation-specific group logic leaking into shared geometry."""

    analysis = analyze_parallel_bases_trapezoid(coordinates)
    assert analysis.base_lengths == base_lengths
    assert analysis.height == height
    assert analysis.area == area
    assert analysis.area_by_coordinates == area


def test_parallel_bases_reject_non_trapezoid_quadrilateral() -> None:
    """Catch applying the base formula without exactly one parallel pair."""

    with pytest.raises(ValueError, match="parallel"):
        analyze_parallel_bases_trapezoid(((1, 1), (3, 2), (4, 5), (1, 4)))


@pytest.mark.parametrize(
    ("coordinates", "area"),
    [
        (((3, 6), (1, 3), (4, 1), (6, 3)), Fraction(25, 2)),
        (((4, 1), (7, 5), (4, 3), (1, 5)), Fraction(6)),
        (((3, 4), (1, 1), (4, 3), (2, 2)), Fraction(1)),
        (((4, 5), (1, 2), (5, 1), (3, 3)), Fraction(9, 2)),
    ],
)
def test_ordered_quadrilateral_area_supports_concavity(
    coordinates: tuple[tuple[int, int], ...],
    area: Fraction,
) -> None:
    """Keep shoelace area exact for convex and concave ordered parents."""

    assert quadrilateral_coordinate_area(coordinates) == area


def test_ordered_quadrilateral_rejects_self_intersection() -> None:
    """Never interpret a bow-tie point order as one child-facing polygon."""

    with pytest.raises(ValueError, match="self-intersect"):
        quadrilateral_coordinate_area(((1, 1), (4, 4), (1, 4), (4, 1)))


@pytest.mark.parametrize(
    ("coordinates", "interior", "boundary"),
    [
        (((3, 6), (1, 3), (4, 1), (6, 3)), 10, 7),
        (((4, 1), (7, 5), (4, 3), (1, 5)), 5, 4),
        (((3, 4), (1, 1), (4, 3), (2, 2)), 0, 4),
        (((4, 5), (1, 2), (5, 1), (3, 3)), 2, 7),
    ],
)
def test_lattice_point_counts_are_enumerated_for_pick_solution(
    coordinates: tuple[tuple[int, int], ...],
    interior: int,
    boundary: int,
) -> None:
    """Count child-visible interior and boundary nodes without deriving either from Pick."""

    calculator = getattr(quadrilateral_geometry, "lattice_point_counts", None)
    assert callable(calculator), "lattice point counter is not implemented"
    assert calculator(coordinates) == (interior, boundary)
    assert Fraction(interior) + Fraction(boundary, 2) - 1 == (
        quadrilateral_coordinate_area(coordinates)
    )


def test_pick_enumeration_returns_exact_disjoint_node_sets() -> None:
    """Expose the exact nodes that the Pick diagram and formula share."""

    nodes = enumerate_lattice_points(((1, 1), (4, 1), (4, 4), (1, 4)))

    assert nodes.interior == ((2, 2), (3, 2), (2, 3), (3, 3))
    assert len(nodes.boundary) == 12
    assert (1, 1) in nodes.boundary
    assert (4, 4) in nodes.boundary
    assert set(nodes.interior).isdisjoint(nodes.boundary)
