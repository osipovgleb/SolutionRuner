"""Analyze square-grid triangles and require independent area agreement."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


class GeometryMismatchError(ValueError):
    """Report disagreement between a strategy formula and coordinate area."""


@dataclass(frozen=True)
class AxisAlignedTriangleAnalysis:
    """Describe one triangle with exactly one horizontal or vertical base."""

    base_start: tuple[int, int]
    base_end: tuple[int, int]
    apex: tuple[int, int]
    altitude_foot: tuple[int, int]
    base_length: int
    height: int
    area: Fraction
    area_by_coordinates: Fraction


@dataclass(frozen=True)
class RightTriangleAnalysis:
    """Describe one grid triangle with axis-aligned perpendicular catheti."""

    right_angle: tuple[int, int]
    cathetus_lengths: tuple[int, int]
    area: Fraction
    area_by_coordinates: Fraction


def triangle_coordinate_area(points: tuple[tuple[int, int], ...]) -> Fraction:
    """Return exact triangle area from the shoelace formula."""

    if len(points) != 3 or len(set(points)) != 3:
        raise ValueError("triangle must contain three distinct points")
    doubled = abs(
        sum(
            first[0] * second[1] - first[1] * second[0]
            for first, second in zip(points, points[1:] + points[:1])
        )
    )
    if doubled == 0:
        raise ValueError("triangle has zero area")
    return Fraction(doubled, 2)


def verify_triangle_area(
    points: tuple[tuple[int, int], ...],
    independently_computed: Fraction,
) -> Fraction:
    """Return coordinate area only when both triangle calculations agree."""

    coordinate_area = triangle_coordinate_area(points)
    if coordinate_area != independently_computed:
        raise GeometryMismatchError("triangle area calculations disagree")
    return coordinate_area


def analyze_axis_aligned_triangle(
    points: tuple[tuple[int, int], ...],
) -> AxisAlignedTriangleAnalysis:
    """Analyze the unique horizontal or vertical base and perpendicular height."""

    if len(points) != 3 or len(set(points)) != 3:
        raise ValueError("triangle must contain three distinct points")
    candidates = [
        (first, second)
        for index, first in enumerate(points)
        for second in points[index + 1 :]
        if first[0] == second[0] or first[1] == second[1]
    ]
    if len(candidates) != 1:
        raise ValueError("triangle must contain exactly one axis-aligned base")
    first, second = candidates[0]
    if first[0] == second[0]:
        base_start, base_end = sorted((first, second), key=lambda point: point[1])
        apex = next(point for point in points if point not in {first, second})
        altitude_foot = (first[0], apex[1])
        base_length = abs(second[1] - first[1])
        height = abs(apex[0] - first[0])
    else:
        base_start, base_end = sorted((first, second), key=lambda point: point[0])
        apex = next(point for point in points if point not in {first, second})
        altitude_foot = (apex[0], first[1])
        base_length = abs(second[0] - first[0])
        height = abs(apex[1] - first[1])
    area = Fraction(base_length * height, 2)
    coordinate_area = verify_triangle_area(points, area)
    return AxisAlignedTriangleAnalysis(
        base_start=base_start,
        base_end=base_end,
        apex=apex,
        altitude_foot=altitude_foot,
        base_length=base_length,
        height=height,
        area=area,
        area_by_coordinates=coordinate_area,
    )


def analyze_right_triangle(
    points: tuple[tuple[int, int], ...],
) -> RightTriangleAnalysis:
    """Analyze one right triangle with horizontal and vertical catheti."""

    if len(points) != 3 or len(set(points)) != 3:
        raise ValueError("triangle must contain three distinct points")
    candidates: list[tuple[tuple[int, int], int, int]] = []
    for index, vertex in enumerate(points):
        others = [point for other_index, point in enumerate(points) if other_index != index]
        horizontal = next(
            (abs(point[0] - vertex[0]) for point in others if point[1] == vertex[1]),
            None,
        )
        vertical = next(
            (abs(point[1] - vertex[1]) for point in others if point[0] == vertex[0]),
            None,
        )
        if horizontal and vertical:
            candidates.append((vertex, horizontal, vertical))
    if len(candidates) != 1:
        raise ValueError("triangle must contain one axis-aligned right angle")
    right_angle, horizontal, vertical = candidates[0]
    area = Fraction(horizontal * vertical, 2)
    coordinate_area = verify_triangle_area(points, area)
    return RightTriangleAnalysis(
        right_angle=right_angle,
        cathetus_lengths=(horizontal, vertical),
        area=area,
        area_by_coordinates=coordinate_area,
    )
