"""Validate snapped grid polygons and simplify collinear vertices."""

from __future__ import annotations


class GridPolygonError(ValueError):
    """Report a condition SVG that cannot be frozen safely."""


def _remove_intermediate_collinear_points(
    points: list[tuple[int, int]],
    *,
    expected_vertices: int | None,
) -> tuple[list[tuple[int, int]], int]:
    """Drop only cyclic vertices lying between their collinear neighbors."""

    simplified = list(points)
    discarded = 0
    minimum_vertices = expected_vertices if expected_vertices is not None else 3
    while len(simplified) > minimum_vertices:
        for index, current in enumerate(simplified):
            previous = simplified[index - 1]
            following = simplified[(index + 1) % len(simplified)]
            cross = (current[0] - previous[0]) * (following[1] - current[1]) - (
                current[1] - previous[1]
            ) * (following[0] - current[0])
            between = min(previous[0], following[0]) <= current[0] <= max(
                previous[0], following[0]
            ) and min(previous[1], following[1]) <= current[1] <= max(
                previous[1], following[1]
            )
            if cross == 0 and between:
                simplified.pop(index)
                discarded += 1
                break
        else:
            break
    return simplified, discarded


def _validate_geometry(
    points: tuple[tuple[int, int], ...],
    *,
    expected_vertices: int | None,
    geometry_profile: str,
) -> None:
    """Reject snapped points that do not match the selected pure strategy."""

    if expected_vertices is None:
        if geometry_profile != "grid-cell-count":
            raise GridPolygonError(
                "variable vertex count requires grid-cell-count geometry"
            )
        if len(points) < 4 or len(set(points)) != len(points):
            raise GridPolygonError(
                "cell figure must contain at least four distinct points"
            )
        if any(
            first[0] != second[0] and first[1] != second[1]
            for first, second in zip(points, points[1:] + points[:1])
        ):
            raise GridPolygonError("cell figure edges must follow square-grid lines")
    elif len(points) != expected_vertices or len(set(points)) != expected_vertices:
        raise GridPolygonError(
            f"snapped SVG polygon does not contain {expected_vertices} distinct points"
        )
    doubled_area = abs(
        sum(
            first[0] * second[1] - first[1] * second[0]
            for first, second in zip(points, points[1:] + points[:1])
        )
    )
    if doubled_area == 0:
        raise GridPolygonError("snapped SVG polygon has zero area")
    if expected_vertices is None:
        return
    if expected_vertices == 3:
        if geometry_profile == "right-triangle":
            right_angles = 0
            for index, vertex in enumerate(points):
                others = [
                    point
                    for other_index, point in enumerate(points)
                    if other_index != index
                ]
                first = (others[0][0] - vertex[0], others[0][1] - vertex[1])
                second = (others[1][0] - vertex[0], others[1][1] - vertex[1])
                right_angles += first[0] * second[0] + first[1] * second[1] == 0
            if right_angles != 1:
                raise GridPolygonError("snapped SVG triangle has no unique right angle")
        elif geometry_profile == "base-height-triangle":
            axis_aligned = sum(
                first[0] == second[0] or first[1] == second[1]
                for index, first in enumerate(points)
                for second in points[index + 1 :]
            )
            if axis_aligned != 1:
                raise GridPolygonError(
                    "snapped SVG triangle must have one axis-aligned base"
                )
        elif geometry_profile != "bounding-rectangle-triangle":
            raise GridPolygonError(
                f"unsupported triangle geometry profile: {geometry_profile}"
            )
    elif expected_vertices == 4:
        if geometry_profile in {
            "parallel-bases-trapezoid",
            "parallel-bases-trapezoid-three-methods",
            "trapezoid-pick",
        }:
            edges = [
                (
                    points[(index + 1) % 4][0] - points[index][0],
                    points[(index + 1) % 4][1] - points[index][1],
                )
                for index in range(4)
            ]
            parallel = sum(
                edges[first][0] * edges[second][1] == edges[first][1] * edges[second][0]
                for first, second in ((0, 2), (1, 3))
            )
            if parallel != 1:
                raise GridPolygonError(
                    "snapped SVG quadrilateral has no unique parallel pair"
                )
        elif geometry_profile not in {
            "bounding-rectangle-quadrilateral",
            "bounding-rectangle-trapezoid",
            "parallelogram-three-methods",
        }:
            raise GridPolygonError(
                f"unsupported quadrilateral geometry profile: {geometry_profile}"
            )
    else:
        raise GridPolygonError(
            f"unsupported expected vertex count: {expected_vertices}"
        )
