"""Recover visible polygon contours from SVG shapes and line segments."""

import itertools
import math
import re
import statistics
from xml.etree import ElementTree

from .polygon_validation import GridPolygonError

_NUMBER_PATTERN = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")
_OUTLINE_STROKES = {
    "#000",
    "#000000",
    "#0d0f0f",
    "#111",
    "#111111",
    "black",
    "rgb(0,0,0)",
}


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
        numbers = [
            float(value)
            for value in _NUMBER_PATTERN.findall(str(element.get("points") or ""))
        ]
        if len(numbers) < 6 or len(numbers) % 2:
            continue
        raw = list(zip(numbers[0::2], numbers[1::2]))
        points: list[tuple[float, float]] = []
        for point in raw:
            if (
                points
                and max(abs(point[0] - points[-1][0]), abs(point[1] - points[-1][1]))
                <= 1.0
            ):
                continue
            points.append(point)
        is_closed = (
            len(points) > 3
            and max(
                abs(points[0][0] - points[-1][0]),
                abs(points[0][1] - points[-1][1]),
            )
            <= 1.0
        )
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
        distance = (
            0 if expected_vertices is None else abs(len(points) - expected_vertices)
        )
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


def _visible_outline_segments(root, parents, bounds):
    """Collect non-degenerate dark segments within the visible SVG bounds."""

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
            for start, end in itertools.pairwise(element_points)
            if max(abs(start[0] - end[0]), abs(start[1] - end[1])) > 1.0
        )
    if not segments:
        raise GridPolygonError("SVG has no non-degenerate polygon or dark line outline")

    return segments


def _endpoint_graph(segments):
    """Join nearby segment endpoints and build an undirected adjacency graph."""

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

    return centers, adjacency


def _line_outline_points(
    root: ElementTree.Element,
    parents: dict[ElementTree.Element, ElementTree.Element],
    *,
    expected_vertices: int | None,
    bounds: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    """Recover the largest closed dark outline stored as separate SVG lines."""

    segments = _visible_outline_segments(root, parents, bounds)
    centers, adjacency = _endpoint_graph(segments)
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
            projection = (current[0] - previous[0]) * dx + (
                current[1] - previous[1]
            ) * dy
            distance = abs(
                dx * (previous[1] - current[1]) - (previous[0] - current[0]) * dy
            ) / math.sqrt(squared_length)
            if 0 <= projection <= squared_length and distance <= tolerance:
                simplified.pop(index)
                break
        else:
            break
    return simplified
