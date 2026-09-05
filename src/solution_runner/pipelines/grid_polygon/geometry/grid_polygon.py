"""Extract one canonical integer polygon from a square-grid SVG asset."""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import math
import re
import statistics
from typing import Iterable
from xml.etree import ElementTree


_NUMBER_PATTERN = re.compile(
    r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
)
_GRID_STROKES = {
    "#adaaaa",
    "#bfbfbf",
    "rgb(173,170,170)",
    "rgb(191,191,191)",
}
_OUTLINE_STROKES = {
    "#000",
    "#000000",
    "#0d0f0f",
    "#111",
    "#111111",
    "black",
    "rgb(0,0,0)",
}


class GridPolygonError(ValueError):
    """Report a condition SVG that cannot be frozen safely."""


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
            or any(isinstance(value, bool) or not isinstance(value, int) for value in point)
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


def _local_name(tag: str) -> str:
    """Return an XML tag without its namespace."""

    return tag.rsplit("}", 1)[-1]


def _number(element: ElementTree.Element, name: str) -> float:
    """Read one required finite SVG numeric attribute."""

    raw = str(element.get(name) or "").strip()
    match = re.match(r"^[-+]?(?:\d+(?:\.\d*)?|\.\d+)", raw)
    if match is None:
        raise GridPolygonError(f"SVG {name} is missing or non-numeric")
    value = float(match.group(0))
    if not math.isfinite(value):
        raise GridPolygonError(f"SVG {name} is not finite")
    return value


def _view_bounds(root: ElementTree.Element) -> tuple[float, float, float, float]:
    """Return finite visible SVG min/max bounds."""

    values = [float(value) for value in _NUMBER_PATTERN.findall(str(root.get("viewBox") or ""))]
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


def _effective_property(
    element: ElementTree.Element,
    parents: dict[ElementTree.Element, ElementTree.Element],
    name: str,
) -> str:
    """Resolve one direct, styled, or inherited SVG presentation property."""

    current: ElementTree.Element | None = element
    while current is not None:
        direct = str(current.get(name) or "").strip()
        if direct:
            return direct
        for declaration in str(current.get("style") or "").split(";"):
            key, separator, value = declaration.partition(":")
            if separator and key.strip() == name and value.strip():
                return value.strip()
        current = parents.get(current)
    return ""


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
        for previous, current in zip(values, values[1:])
        if current - previous > 2.0
    ]
    if len(differences) < 2:
        raise GridPolygonError("SVG does not contain enough repeated grid intervals")
    median = statistics.median(differences)
    close = [difference for difference in differences if 0.75 <= difference / median <= 1.25]
    if len(close) < max(2, len(differences) // 2):
        raise GridPolygonError("SVG grid intervals are inconsistent")
    return statistics.median(close)


def _polygon_area(points: list[tuple[float, float]]) -> float:
    """Return doubled absolute polygon area in SVG coordinates."""

    return abs(
        sum(
            x1 * y2 - y1 * x2
            for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
        )
    )


def _polygon_points(
    root: ElementTree.Element,
    parents: dict[ElementTree.Element, ElementTree.Element],
    *,
    expected_vertices: int | None,
    bounds: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    """Choose the closest visible outlined polygon from one SVG."""

    choices: list[tuple[int, bool, bool, float, list[tuple[float, float]]]] = []
    min_x, min_y, max_x, max_y = bounds
    for element in root.iter():
        local_name = _local_name(element.tag)
        if local_name not in {"polygon", "polyline"}:
            continue
        numbers = [float(value) for value in _NUMBER_PATTERN.findall(str(element.get("points") or ""))]
        if len(numbers) < 6 or len(numbers) % 2:
            continue
        raw = list(zip(numbers[0::2], numbers[1::2]))
        points: list[tuple[float, float]] = []
        for point in raw:
            if points and max(abs(point[0] - points[-1][0]), abs(point[1] - points[-1][1])) <= 1.0:
                continue
            points.append(point)
        is_closed = len(points) > 3 and max(
            abs(points[0][0] - points[-1][0]),
            abs(points[0][1] - points[-1][1]),
        ) <= 1.0
        if local_name == "polyline" and not is_closed:
            continue
        if is_closed:
            points.pop()
        area = _polygon_area(points)
        if area == 0:
            continue
        intersects = (
            max(point[0] for point in points) >= min_x
            and min(point[0] for point in points) <= max_x
            and max(point[1] for point in points) >= min_y
            and min(point[1] for point in points) <= max_y
        )
        fill = _effective_property(element, parents, "fill").lower()
        stroke = _effective_property(element, parents, "stroke").lower()
        is_outline = fill == "none" or bool(stroke and stroke != "none")
        distance = 0 if expected_vertices is None else abs(len(points) - expected_vertices)
        choices.append((distance, intersects, is_outline, area, points))
    if not choices:
        return _line_outline_points(
            root,
            parents,
            expected_vertices=expected_vertices,
            bounds=bounds,
        )
    visible = [choice for choice in choices if choice[1]] or choices
    closest = min(choice[0] for choice in visible)
    candidates = [choice for choice in visible if choice[0] == closest]
    candidates = [choice for choice in candidates if choice[2]] or candidates
    return max(candidates, key=lambda choice: choice[3])[4]


def _line_outline_points(
    root: ElementTree.Element,
    parents: dict[ElementTree.Element, ElementTree.Element],
    *,
    expected_vertices: int | None,
    bounds: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    """Recover the largest closed dark outline stored as separate SVG lines."""

    min_x, min_y, max_x, max_y = bounds
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for element in root.iter():
        local_name = _local_name(element.tag)
        if local_name not in {"line", "polyline"}:
            continue
        stroke = re.sub(
            r"\s+",
            "",
            _effective_property(element, parents, "stroke").lower(),
        )
        if stroke not in _OUTLINE_STROKES:
            continue
        if local_name == "line":
            try:
                element_points = [
                    (_number(element, "x1"), _number(element, "y1")),
                    (_number(element, "x2"), _number(element, "y2")),
                ]
            except GridPolygonError:
                continue
        else:
            numbers = [
                float(value)
                for value in _NUMBER_PATTERN.findall(str(element.get("points") or ""))
            ]
            if len(numbers) < 4 or len(numbers) % 2:
                continue
            element_points = list(zip(numbers[::2], numbers[1::2], strict=True))
        margin = 1.5
        if not all(
            min_x - margin <= x <= max_x + margin
            and min_y - margin <= y <= max_y + margin
            for x, y in element_points
        ):
            continue
        segments.extend(
            (start, end)
            for start, end in zip(element_points, element_points[1:])
            if max(abs(start[0] - end[0]), abs(start[1] - end[1])) > 1.0
        )
    if not segments:
        raise GridPolygonError("SVG has no non-degenerate polygon or dark line outline")

    clusters: list[list[tuple[float, float]]] = []

    def cluster_index(point: tuple[float, float]) -> int:
        """Return one stable endpoint cluster for slightly drifting line joins."""

        for index, cluster in enumerate(clusters):
            center_x = statistics.fmean(value[0] for value in cluster)
            center_y = statistics.fmean(value[1] for value in cluster)
            if max(abs(point[0] - center_x), abs(point[1] - center_y)) <= 1.5:
                cluster.append(point)
                return index
        clusters.append([point])
        return len(clusters) - 1

    edges: set[tuple[int, int]] = set()
    for start, end in segments:
        first, second = cluster_index(start), cluster_index(end)
        if first != second:
            edges.add(tuple(sorted((first, second))))
    centers = [
        (
            statistics.fmean(point[0] for point in cluster),
            statistics.fmean(point[1] for point in cluster),
        )
        for cluster in clusters
    ]
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(centers))}
    for first, second in edges:
        adjacency[first].add(second)
        adjacency[second].add(first)

    cycles: list[list[tuple[float, float]]] = []
    unseen = set(adjacency)
    while unseen:
        seed = min(unseen)
        component: set[int] = set()
        pending = [seed]
        while pending:
            current = pending.pop()
            if current in component:
                continue
            component.add(current)
            pending.extend(adjacency[current] - component)
        unseen -= component
        if len(component) < 3 or any(len(adjacency[index]) != 2 for index in component):
            continue
        start = min(component, key=lambda index: centers[index])
        previous: int | None = None
        current = start
        ordering: list[int] = []
        while True:
            ordering.append(current)
            choices = sorted(
                (index for index in adjacency[current] if index != previous),
                key=lambda index: centers[index],
            )
            if not choices:
                ordering = []
                break
            following = choices[0]
            if following == start:
                break
            if following in ordering:
                ordering = []
                break
            previous, current = current, following
        if len(ordering) != len(component):
            continue
        points = _simplify_raw_cycle(
            [centers[index] for index in ordering],
            minimum_vertices=expected_vertices or 3,
        )
        if expected_vertices is not None and len(points) < expected_vertices:
            continue
        if _polygon_area(points) > 0:
            cycles.append(points)
    if not cycles:
        raise GridPolygonError("SVG dark outline does not form one closed polygon")
    return max(cycles, key=_polygon_area)


def _simplify_raw_cycle(
    points: list[tuple[float, float]],
    *,
    minimum_vertices: int,
    tolerance: float = 1.5,
) -> list[tuple[float, float]]:
    """Remove sampled points lying within tolerance of one straight edge."""

    simplified = list(points)
    while len(simplified) > minimum_vertices:
        for index, current in enumerate(simplified):
            previous = simplified[index - 1]
            following = simplified[(index + 1) % len(simplified)]
            dx = following[0] - previous[0]
            dy = following[1] - previous[1]
            squared_length = dx * dx + dy * dy
            if squared_length == 0:
                continue
            projection = (
                (current[0] - previous[0]) * dx
                + (current[1] - previous[1]) * dy
            )
            distance = abs(
                dx * (previous[1] - current[1])
                - (previous[0] - current[0]) * dy
            ) / math.sqrt(squared_length)
            if 0 <= projection <= squared_length and distance <= tolerance:
                simplified.pop(index)
                break
        else:
            break
    return simplified


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
            cross = (
                (current[0] - previous[0]) * (following[1] - current[1])
                - (current[1] - previous[1]) * (following[0] - current[0])
            )
            between = (
                min(previous[0], following[0]) <= current[0] <= max(previous[0], following[0])
                and min(previous[1], following[1]) <= current[1] <= max(previous[1], following[1])
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
            raise GridPolygonError("variable vertex count requires grid-cell-count geometry")
        if len(points) < 4 or len(set(points)) != len(points):
            raise GridPolygonError("cell figure must contain at least four distinct points")
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
                others = [point for other_index, point in enumerate(points) if other_index != index]
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
                raise GridPolygonError("snapped SVG triangle must have one axis-aligned base")
        elif geometry_profile != "bounding-rectangle-triangle":
            raise GridPolygonError(f"unsupported triangle geometry profile: {geometry_profile}")
    elif expected_vertices == 4:
        if geometry_profile == "parallel-bases-trapezoid":
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
                raise GridPolygonError("snapped SVG quadrilateral has no unique parallel pair")
        elif geometry_profile not in {
            "bounding-rectangle-quadrilateral",
            "bounding-rectangle-trapezoid",
            "parallelogram-three-methods",
        }:
            raise GridPolygonError(f"unsupported quadrilateral geometry profile: {geometry_profile}")
    else:
        raise GridPolygonError(f"unsupported expected vertex count: {expected_vertices}")


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
        stroke = re.sub(r"\s+", "", _effective_property(element, parents, "stroke").lower())
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
        (x - min(point[0] for point in simplified) + 1, y - min(point[1] for point in simplified) + 1)
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
