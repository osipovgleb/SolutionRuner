"""Analyze four-point grid polygons with independently verified exact areas."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isqrt

from .triangle import GeometryMismatchError


@dataclass(frozen=True)
class ParallelBasesTrapezoidAnalysis:
    """Describe one trapezoid with one pair of parallel opposite sides."""

    base_lengths: tuple[int, int]
    height: Fraction
    area: Fraction
    area_by_coordinates: Fraction


@dataclass(frozen=True)
class LatticePointSet:
    """Carry the exact interior and boundary nodes used by Pick's formula."""

    interior: tuple[tuple[int, int], ...]
    boundary: tuple[tuple[int, int], ...]


def _cross(first: tuple[int, int], second: tuple[int, int]) -> int:
    """Return the two-dimensional vector cross product."""

    return first[0] * second[1] - first[1] * second[0]


def _subtract(first: tuple[int, int], second: tuple[int, int]) -> tuple[int, int]:
    """Return the vector from the second point to the first."""

    return first[0] - second[0], first[1] - second[1]


def convex_hull(points: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    """Return a counter-clockwise hull containing every distinct input point."""

    unique = sorted(set(points))
    if len(unique) < 3:
        raise ValueError("polygon must contain at least three distinct points")

    def build_half(values: list[tuple[int, int]]) -> list[tuple[int, int]]:
        """Build one monotone hull half while discarding interior collinear points."""

        half: list[tuple[int, int]] = []
        for point in values:
            while len(half) >= 2 and _cross(
                _subtract(half[-1], half[-2]),
                _subtract(point, half[-1]),
            ) <= 0:
                half.pop()
            half.append(point)
        return half

    hull = build_half(unique)[:-1] + build_half(list(reversed(unique)))[:-1]
    if len(hull) != len(unique):
        raise ValueError("polygon points must form one strict convex hull")
    return tuple(hull)


def quadrilateral_coordinate_area(points: tuple[tuple[int, int], ...]) -> Fraction:
    """Return exact area for one simple ordered convex or concave quadrilateral."""

    if len(points) != 4 or len(set(points)) != 4:
        raise ValueError("quadrilateral must contain four distinct ordered vertices")
    for first, second in ((0, 2), (1, 3)):
        if _segments_intersect(
            points[first],
            points[(first + 1) % 4],
            points[second],
            points[(second + 1) % 4],
        ):
            raise ValueError("quadrilateral edges self-intersect")
    doubled = sum(
        _cross(points[index], points[(index + 1) % 4])
        for index in range(4)
    )
    if doubled == 0:
        raise ValueError("quadrilateral has zero area")
    return Fraction(abs(doubled), 2)


def _segments_intersect(
    first_start: tuple[int, int],
    first_end: tuple[int, int],
    second_start: tuple[int, int],
    second_end: tuple[int, int],
) -> bool:
    """Return whether two closed integer segments share any point."""

    def orientation(
        start: tuple[int, int],
        end: tuple[int, int],
        point: tuple[int, int],
    ) -> int:
        """Return the signed turn from one segment to a point."""

        return _cross(_subtract(end, start), _subtract(point, start))

    def contains(
        start: tuple[int, int],
        end: tuple[int, int],
        point: tuple[int, int],
    ) -> bool:
        """Return whether a collinear point lies on one closed segment."""

        return (
            min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
            and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
        )

    first_second = orientation(first_start, first_end, second_start)
    first_end_second = orientation(first_start, first_end, second_end)
    second_first = orientation(second_start, second_end, first_start)
    second_end_first = orientation(second_start, second_end, first_end)
    if (first_second > 0) != (first_end_second > 0) and (
        second_first > 0
    ) != (second_end_first > 0):
        return True
    return (
        (first_second == 0 and contains(first_start, first_end, second_start))
        or (first_end_second == 0 and contains(first_start, first_end, second_end))
        or (second_first == 0 and contains(second_start, second_end, first_start))
        or (second_end_first == 0 and contains(second_start, second_end, first_end))
    )


def lattice_point_counts(
    points: tuple[tuple[int, int], ...],
) -> tuple[int, int]:
    """Count interior and boundary lattice nodes of one simple quadrilateral."""

    nodes = enumerate_lattice_points(points)
    return len(nodes.interior), len(nodes.boundary)


def enumerate_lattice_points(
    points: tuple[tuple[int, int], ...],
) -> LatticePointSet:
    """Return deterministic exact interior and boundary lattice-node sets."""

    quadrilateral_coordinate_area(points)
    boundary_nodes: set[tuple[int, int]] = set()
    for start, end in zip(points, points[1:] + points[:1], strict=True):
        dx, dy = end[0] - start[0], end[1] - start[1]
        steps = gcd(abs(dx), abs(dy))
        if steps == 0:
            raise ValueError("quadrilateral edge has zero length")
        step_x, step_y = dx // steps, dy // steps
        boundary_nodes.update(
            (start[0] + index * step_x, start[1] + index * step_y)
            for index in range(steps)
        )
    xmin, xmax = min(x for x, _ in points), max(x for x, _ in points)
    ymin, ymax = min(y for _, y in points), max(y for _, y in points)
    interior_nodes = {
        (x, y)
        for x in range(xmin + 1, xmax)
        for y in range(ymin + 1, ymax)
        if _point_is_strictly_inside(points, (x, y))
    }
    if interior_nodes & boundary_nodes:
        raise ValueError("interior and boundary lattice nodes overlap")
    ordering = lambda point: (point[1], point[0])
    return LatticePointSet(
        interior=tuple(sorted(interior_nodes, key=ordering)),
        boundary=tuple(sorted(boundary_nodes, key=ordering)),
    )


def _point_is_strictly_inside(
    polygon: tuple[tuple[int, int], ...],
    point: tuple[int, int],
) -> bool:
    """Return winding-number containment while excluding boundary nodes."""

    winding = 0
    for start, end in zip(polygon, polygon[1:] + polygon[:1], strict=True):
        turn = _cross(_subtract(end, start), _subtract(point, start))
        if turn == 0 and (
            min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
            and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
        ):
            return False
        if start[1] <= point[1] < end[1] and turn > 0:
            winding += 1
        elif end[1] <= point[1] < start[1] and turn < 0:
            winding -= 1
    return winding != 0


def _integral_length(vector: tuple[int, int]) -> int:
    """Return an exact integer edge length required by displayed formulas."""

    squared = vector[0] * vector[0] + vector[1] * vector[1]
    length = isqrt(squared)
    if length <= 0 or length * length != squared:
        raise ValueError("parallel base length is not an integer")
    return length


def analyze_parallel_bases_trapezoid(
    points: tuple[tuple[int, int], ...],
) -> ParallelBasesTrapezoidAnalysis:
    """Analyze horizontal, vertical, or integral slanted parallel bases."""

    hull = convex_hull(points)
    if len(hull) != 4:
        raise ValueError("trapezoid must contain four hull vertices")
    edges = [
        _subtract(hull[(index + 1) % 4], hull[index])
        for index in range(4)
    ]
    pairs = [
        pair
        for pair in ((0, 2), (1, 3))
        if _cross(edges[pair[0]], edges[pair[1]]) == 0
    ]
    if len(pairs) != 1:
        raise ValueError("trapezoid must contain exactly one parallel opposite pair")
    first_index, second_index = pairs[0]
    first_length = _integral_length(edges[first_index])
    second_length = _integral_length(edges[second_index])
    height = Fraction(
        abs(
            _cross(
                edges[first_index],
                _subtract(hull[second_index], hull[first_index]),
            )
        ),
        first_length,
    )
    base_lengths = tuple(sorted((first_length, second_length), reverse=True))
    area = Fraction(sum(base_lengths), 2) * height
    coordinate_area = quadrilateral_coordinate_area(points)
    if area != coordinate_area:
        raise GeometryMismatchError("trapezoid area calculations disagree")
    return ParallelBasesTrapezoidAnalysis(
        base_lengths=base_lengths,
        height=height,
        area=area,
        area_by_coordinates=coordinate_area,
    )
