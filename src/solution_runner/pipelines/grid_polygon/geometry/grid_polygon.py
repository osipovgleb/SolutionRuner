"""Extract one canonical integer polygon from a square-grid SVG asset."""

from __future__ import annotations

import ast
import hashlib
import itertools
import math
import re
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from xml.etree import ElementTree

from .polygon_validation import (
    GridPolygonError,
    _remove_intermediate_collinear_points,
    _validate_geometry,
)
from .svg_polygon_outline import (
    _NUMBER_PATTERN,
    _effective_property,
    _local_name,
    _number,
    _polygon_points,
)

_GRID_STROKES = {
    "#adaaaa",
    "#bfbfbf",
    "rgb(173,170,170)",
    "rgb(191,191,191)",
}


@dataclass(frozen=True)
class ParsedGridPolygon:
    """Return normalized coordinates and evidence used to obtain them."""

    coordinates: tuple[tuple[int, int], ...]
    raw_polygon_points: tuple[tuple[float, float], ...]
    grid_step_x: float
    grid_step_y: float
    discarded_intermediate_points: int


def polygon_sha256(svg_bytes: bytes) -> str:
    """Return the stable byte digest used by prepared manifests."""

    return hashlib.sha256(svg_bytes).hexdigest()


def parse_coordinate_alt(
    text: str,
    *,
    expected_vertices: int,
) -> tuple[tuple[int, int], ...]:
    """Parse one exact integer coordinate list stored in asset alt metadata."""

    if not isinstance(text, str) or not text.strip():
        raise GridPolygonError("coordinate alt is empty")
    try:
        decoded = ast.literal_eval(text)
    except (SyntaxError, ValueError) as exc:
        raise GridPolygonError("coordinate alt is invalid") from exc
    if not isinstance(decoded, list) or len(decoded) != expected_vertices:
        raise GridPolygonError(
            f"coordinate alt must contain exactly {expected_vertices} points"
        )
    coordinates: list[tuple[int, int]] = []
    for point in decoded:
        if (
            not isinstance(point, tuple)
            or len(point) != 2
            or any(
                isinstance(value, bool) or not isinstance(value, int) for value in point
            )
        ):
            raise GridPolygonError("coordinate alt points must be integer pairs")
        coordinates.append((point[0], point[1]))
    if len(set(coordinates)) != expected_vertices:
        raise GridPolygonError("coordinate alt points must be distinct")
    return tuple(coordinates)


def serialize_coordinate_alt(coordinates: Iterable[tuple[int, int]]) -> str:
    """Serialize coordinates using the one compact asset-alt representation."""

    points = tuple(coordinates)
    if not points or len(set(points)) != len(points):
        raise GridPolygonError("coordinate alt points must be non-empty and distinct")
    return "[" + ", ".join(f"({x},{y})" for x, y in points) + "]"


def _view_bounds(root: ElementTree.Element) -> tuple[float, float, float, float]:
    """Return finite visible SVG min/max bounds."""

    values = [
        float(value)
        for value in _NUMBER_PATTERN.findall(str(root.get("viewBox") or ""))
    ]
    if len(values) == 4 and all(math.isfinite(value) for value in values):
        min_x, min_y, width, height = values
    else:
        min_x = float(str(root.get("x") or "0").removesuffix("px"))
        min_y = float(str(root.get("y") or "0").removesuffix("px"))
        width = _number(root, "width")
        height = _number(root, "height")
    if width <= 0 or height <= 0:
        raise GridPolygonError("SVG visible bounds are not positive")
    return min_x, min_y, min_x + width, min_y + height


def _dedupe_positions(values: Iterable[float], tolerance: float = 1.0) -> list[float]:
    """Merge nearly identical grid-line coordinates."""

    buckets: list[list[float]] = []
    for value in sorted(values):
        if buckets and abs(value - statistics.fmean(buckets[-1])) <= tolerance:
            buckets[-1].append(value)
        else:
            buckets.append([value])
    return [statistics.fmean(bucket) for bucket in buckets]


def _grid_step(values: list[float]) -> float:
    """Infer one stable interval from ordered grid-line positions."""

    differences = [
        current - previous
        for previous, current in itertools.pairwise(values)
        if current - previous > 2.0
    ]
    if len(differences) < 2:
        raise GridPolygonError("SVG does not contain enough repeated grid intervals")
    median = statistics.median(differences)
    close = [
        difference for difference in differences if 0.75 <= difference / median <= 1.25
    ]
    if len(close) < max(2, len(differences) // 2):
        raise GridPolygonError("SVG grid intervals are inconsistent")
    return statistics.median(close)


def raw_outline_points_from_svg(
    svg_bytes: bytes,
    *,
    expected_vertices: int | None,
) -> tuple[tuple[float, float], ...]:
    """Return the visible polygon or dark line-loop points before grid snapping."""

    try:
        root = ElementTree.fromstring(svg_bytes)
    except ElementTree.ParseError as exc:
        raise GridPolygonError("condition asset is not valid SVG XML") from exc
    parents = {child: parent for parent in root.iter() for child in parent}
    return tuple(
        _polygon_points(
            root,
            parents,
            expected_vertices=expected_vertices,
            bounds=_view_bounds(root),
        )
    )


def parse_grid_polygon(
    svg_bytes: bytes,
    *,
    expected_vertices: int | None,
    geometry_profile: str,
    snap_tolerance: float = 0.15,
) -> ParsedGridPolygon:
    """Extract, snap, normalize, and validate one square-grid polygon."""

    try:
        root = ElementTree.fromstring(svg_bytes)
    except ElementTree.ParseError as exc:
        raise GridPolygonError("condition asset is not valid SVG XML") from exc
    parents = {child: parent for parent in root.iter() for child in parent}
    bounds = _view_bounds(root)
    polygon = _polygon_points(
        root,
        parents,
        expected_vertices=expected_vertices,
        bounds=bounds,
    )
    horizontal: list[float] = []
    vertical: list[float] = []
    min_x, min_y, max_x, max_y = bounds
    for element in root.iter():
        if _local_name(element.tag) != "line":
            continue
        stroke = re.sub(
            r"\s+", "", _effective_property(element, parents, "stroke").lower()
        )
        if stroke not in _GRID_STROKES:
            continue
        try:
            x1, y1 = _number(element, "x1"), _number(element, "y1")
            x2, y2 = _number(element, "x2"), _number(element, "y2")
        except GridPolygonError:
            continue
        margin = 1.5
        intersects = (
            max(x1, x2) >= min_x - margin
            and min(x1, x2) <= max_x + margin
            and max(y1, y2) >= min_y - margin
            and min(y1, y2) <= max_y + margin
        )
        if not intersects:
            continue
        if abs(x1 - x2) <= 1.0 and abs(y1 - y2) >= 10.0:
            vertical.append((x1 + x2) / 2)
        if abs(y1 - y2) <= 1.0 and abs(x1 - x2) >= 10.0:
            horizontal.append((y1 + y2) / 2)
    xs = _dedupe_positions(vertical)
    ys = _dedupe_positions(horizontal)
    if len(xs) < 4 or len(ys) < 4:
        raise GridPolygonError("SVG has too few square-grid lines")
    x_step = _grid_step(xs)
    y_step = _grid_step(ys)
    if max(x_step, y_step) / min(x_step, y_step) > 1.18:
        raise GridPolygonError("SVG grid is not square")

    snapped: list[tuple[int, int]] = []
    for x, y in polygon:
        x_index = min(range(len(xs)), key=lambda index: abs(xs[index] - x))
        y_index = min(range(len(ys)), key=lambda index: abs(ys[index] - y))
        if abs(xs[x_index] - x) / x_step > snap_tolerance:
            raise GridPolygonError("polygon x-coordinate is too far from the grid")
        if abs(ys[y_index] - y) / y_step > snap_tolerance:
            raise GridPolygonError("polygon y-coordinate is too far from the grid")
        snapped.append((x_index, y_index))
    simplified, discarded = _remove_intermediate_collinear_points(
        snapped,
        expected_vertices=expected_vertices,
    )
    if not simplified:
        raise GridPolygonError("snapped SVG polygon is empty")
    normalized = tuple(
        (
            x - min(point[0] for point in simplified) + 1,
            y - min(point[1] for point in simplified) + 1,
        )
        for x, y in simplified
    )
    _validate_geometry(
        normalized,
        expected_vertices=expected_vertices,
        geometry_profile=geometry_profile,
    )
    return ParsedGridPolygon(
        coordinates=normalized,
        raw_polygon_points=tuple(polygon),
        grid_step_x=x_step,
        grid_step_y=y_step,
        discarded_intermediate_points=discarded,
    )


def ordered_coordinates_from_svg(
    svg_bytes: bytes,
    coordinates: tuple[tuple[int, int], ...],
) -> tuple[tuple[int, int], ...]:
    """Return the SVG polygon's cyclic traversal over one canonical point set."""

    profile = (
        "bounding-rectangle-triangle"
        if len(coordinates) == 3
        else "bounding-rectangle-quadrilateral"
    )
    parsed = parse_grid_polygon(
        svg_bytes,
        expected_vertices=len(coordinates),
        geometry_profile=profile,
    )
    if len(parsed.coordinates) != len(coordinates):
        raise GridPolygonError("SVG traversal and canonical coordinates disagree")
    return parsed.coordinates
