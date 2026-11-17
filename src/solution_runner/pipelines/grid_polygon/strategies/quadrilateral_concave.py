"""Construct exact rectangle complements for concave quadrilaterals."""

from __future__ import annotations

from fractions import Fraction

from ..models import GeometryAnalysis
from .bounding_rectangle_triangle import (
    _analyze_complement,
    _analyze_ordered_complement,
)


def _signed_doubled_area(points: tuple[tuple[int, int], ...]) -> int:
    """Return ordered signed doubled area."""

    return sum(
        start[0] * end[1] - start[1] * end[0]
        for start, end in zip(points, points[1:] + points[:1], strict=True)
    )


def _counterclockwise(
    points: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    """Return one stable positive-area traversal without changing adjacency."""

    return points if _signed_doubled_area(points) > 0 else tuple(reversed(points))


def _is_x_monotone(points: tuple[tuple[int, int], ...]) -> bool:
    """Return whether every open vertical slice meets one connected interval."""

    xs = sorted({point[0] for point in points})
    for left, right in zip(xs, xs[1:]):
        probe = Fraction(left + right, 2)
        intersections = 0
        for start, end in zip(points, points[1:] + points[:1], strict=True):
            low, high = sorted((start[0], end[0]))
            if low < probe < high:
                intersections += 1
        if intersections != 2:
            return False
    return True


def _unswap_point(point: tuple[int, int]) -> tuple[int, int]:
    """Return one point from transposed analysis coordinates."""

    return point[1], point[0]


def _unswap_analysis(
    analysis: GeometryAnalysis,
    points: tuple[tuple[int, int], ...],
) -> GeometryAnalysis:
    """Map transposed construction lines back to condition coordinates."""

    xmin, ymin, xmax, ymax = analysis.details["bounds"]
    return GeometryAnalysis(
        area=analysis.area,
        area_by_coordinates=analysis.area_by_coordinates,
        details={
            **analysis.details,
            "points": points,
            "bounds": (ymin, xmin, ymax, xmax),
            "rectangle_width": analysis.details["rectangle_height"],
            "rectangle_height": analysis.details["rectangle_width"],
            "projections": tuple(
                (_unswap_point(start), _unswap_point(end))
                for start, end in analysis.details["projections"]
            ),
            "decomposition_lines": tuple(
                (_unswap_point(start), _unswap_point(end))
                for start, end in analysis.details["decomposition_lines"]
            ),
        },
    )


def _direct_concave_complement(
    points: tuple[tuple[int, int], ...],
    area: Fraction,
) -> GeometryAnalysis | None:
    """Return one exact monotone rectangle complement, trying both grid axes."""

    for swapped in (False, True):
        transformed = tuple((y, x) for x, y in points) if swapped else points
        ordered = _counterclockwise(transformed)
        if not _is_x_monotone(ordered):
            continue
        try:
            analysis = _analyze_ordered_complement(ordered, area)
        except ValueError:
            continue
        if swapped:
            analysis = _unswap_analysis(analysis, points)
        else:
            analysis = GeometryAnalysis(
                area=analysis.area,
                area_by_coordinates=analysis.area_by_coordinates,
                details={**analysis.details, "points": points},
            )
        return GeometryAnalysis(
            area=analysis.area,
            area_by_coordinates=analysis.area_by_coordinates,
            details={**analysis.details, "construction_mode": "rectangle-complement"},
        )
    return None


def _concave_triangle_fallback(
    points: tuple[tuple[int, int], ...],
    area: Fraction,
) -> GeometryAnalysis:
    """Represent one non-monotone concave quadrilateral as hull minus notch."""

    ordered = _counterclockwise(points)
    turns = tuple(
        (current[0] - previous[0]) * (following[1] - current[1])
        - (current[1] - previous[1]) * (following[0] - current[0])
        for previous, current, following in (
            (ordered[index - 1], ordered[index], ordered[(index + 1) % 4])
            for index in range(4)
        )
    )
    reflex = [index for index, turn in enumerate(turns) if turn < 0]
    if len(reflex) != 1:
        raise ValueError("concave quadrilateral must have one reflex vertex")
    reflex_index = reflex[0]
    outer_points = tuple(
        point for index, point in enumerate(ordered) if index != reflex_index
    )
    notch_points = (
        ordered[reflex_index - 1],
        ordered[reflex_index],
        ordered[(reflex_index + 1) % 4],
    )
    outer = _analyze_complement(outer_points)
    notch = _analyze_complement(notch_points)
    if outer.area - notch.area != area:
        raise ValueError("outer triangle and notch areas disagree")
    return GeometryAnalysis(
        area=area,
        area_by_coordinates=area,
        details={
            "points": points,
            "construction_mode": "outer-triangle-minus-notch",
            "outer_analysis": outer,
            "notch_analysis": notch,
            "notch_edge": (notch_points[0], notch_points[2]),
        },
    )
