"""Recover exact lattice radii from canonical and legacy annulus SVGs."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, hypot
import re
from statistics import median
from xml.etree import ElementTree


_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


class RingGeometryError(ValueError):
    """Report SVG geometry that cannot be verified as one lattice annulus."""


@dataclass(frozen=True)
class RingSvgGeometry:
    """Carry logical radii and their measured SVG-space representation."""

    center: tuple[int, int]
    inner_center: tuple[int, int]
    alignment: str
    outer_point: tuple[int, int]
    inner_point: tuple[int, int]
    outer_radius_squared: int
    inner_radius_squared: int
    svg_center: tuple[float, float]
    svg_outer_radius: float
    svg_inner_radius: float
    grid_cell_size: float


def _local_name(tag: str) -> str:
    """Return one namespace-independent XML element name."""

    return tag.rsplit("}", 1)[-1]


def _line_grid(root: ElementTree.Element) -> tuple[float, float, float]:
    """Return grid cell size and minimum x/y line coordinates."""

    vertical: list[float] = []
    horizontal: list[float] = []
    for element in root.iter():
        if _local_name(element.tag) != "line":
            continue
        try:
            x1 = float(element.get("x1", ""))
            x2 = float(element.get("x2", ""))
            y1 = float(element.get("y1", ""))
            y2 = float(element.get("y2", ""))
        except ValueError:
            continue
        if abs(x1 - x2) <= 1.0 and abs(y1 - y2) > 2.0:
            vertical.append((x1 + x2) / 2.0)
        if abs(y1 - y2) <= 1.0 and abs(x1 - x2) > 2.0:
            horizontal.append((y1 + y2) / 2.0)

    def spacing(values: list[float]) -> float | None:
        ordered = sorted({round(value, 3) for value in values})
        diffs = [right - left for left, right in zip(ordered, ordered[1:]) if right - left > 2.0]
        return median(diffs) if diffs else None

    x_step = spacing(vertical)
    y_step = spacing(horizontal)
    steps = [value for value in (x_step, y_step) if value is not None]
    if not steps:
        raise RingGeometryError("ring SVG has no measurable square grid")
    cell = sum(steps) / len(steps)
    if x_step is not None and y_step is not None and abs(x_step - y_step) / cell > 0.08:
        raise RingGeometryError("ring SVG grid is not square")
    return cell, min(vertical or [0.0]), min(horizontal or [0.0])


def _circle_elements(root: ElementTree.Element) -> list[tuple[float, float, float]]:
    """Return explicit SVG circles with positive radius."""

    circles: list[tuple[float, float, float]] = []
    for element in root.iter():
        if _local_name(element.tag) != "circle":
            continue
        try:
            circle = (
                float(element.get("cx", "")),
                float(element.get("cy", "")),
                float(element.get("r", "")),
            )
        except ValueError:
            continue
        if circle[2] > 0:
            circles.append(circle)
    return circles


def _legacy_path_circles(path_data: str) -> list[tuple[float, float, float]]:
    """Recognize every source circle encoded by a cubic path subpath."""

    matches = re.finditer(
        rf"M\s*({_NUMBER})[\s,]+({_NUMBER})\s*([cC])\s*"
        rf"({_NUMBER})[\s,]+({_NUMBER})[\s,]*"
        rf"({_NUMBER})[\s,]+({_NUMBER})[\s,]*"
        rf"({_NUMBER})[\s,]+({_NUMBER})",
        path_data,
    )
    circles: list[tuple[float, float, float]] = []
    for match in matches:
        start_x, start_y = float(match.group(1)), float(match.group(2))
        command = match.group(3)
        end_x, end_y = float(match.group(8)), float(match.group(9))
        if command == "c":
            end_x += start_x
            end_y += start_y
        radius_x = abs(end_x - start_x)
        radius_y = abs(end_y - start_y)
        radius = (radius_x + radius_y) / 2.0
        if radius > 0 and abs(radius_x - radius_y) / radius <= 0.15:
            circles.append((start_x, end_y, radius))
    return circles


def _circle_like_paths(root: ElementTree.Element) -> list[tuple[float, float, float]]:
    """Return legacy source circles recovered from path commands."""

    circles: list[tuple[float, float, float]] = []
    outlines: list[tuple[float, float, float]] = []
    for element in root.iter():
        if _local_name(element.tag) != "path":
            continue
        recovered = _legacy_path_circles(str(element.get("d") or ""))
        circles.extend(recovered)
        style = str(element.get("style") or "").replace(" ", "").lower()
        fill = str(element.get("fill") or "").strip().lower()
        stroke = str(element.get("stroke") or "").strip().lower()
        is_outline = (
            (fill == "none" or "fill:none" in style)
            and (stroke not in {"", "none"} or "stroke:" in style)
        )
        if is_outline:
            outlines.extend(recovered)
    return outlines if len(outlines) >= 2 else circles


def _view_box(root: ElementTree.Element) -> tuple[float, float, float, float]:
    """Return the finite SVG viewport used to reject clipped ring geometry."""

    try:
        values = tuple(float(value) for value in str(root.get("viewBox") or "").split())
    except ValueError as exc:
        raise RingGeometryError("ring SVG has an invalid viewBox") from exc
    if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
        raise RingGeometryError("ring SVG has an invalid viewBox")
    return values


def _require_circle_inside_view_box(
    circle: tuple[float, float, float],
    view_box: tuple[float, float, float, float],
) -> None:
    """Reject a ring whose outer circumference is clipped by the SVG viewport."""

    center_x, center_y, radius = circle
    min_x, min_y, width, height = view_box
    max_x = min_x + width
    max_y = min_y + height
    tolerance = max(width, height) * 1e-9
    if (
        center_x - radius < min_x - tolerance
        or center_x + radius > max_x + tolerance
        or center_y - radius < min_y - tolerance
        or center_y + radius > max_y + tolerance
    ):
        raise RingGeometryError("ring SVG outer circle is outside its viewBox")


def _nearest_lattice_radius_squared(radius_cells: float) -> int:
    """Return the closest non-zero sum of two integer squares."""

    target = radius_cells * radius_cells
    limit = max(2, int(ceil(radius_cells)) + 2)
    representable = {
        dx * dx + dy * dy
        for dx in range(-limit, limit + 1)
        for dy in range(-limit, limit + 1)
        if dx or dy
    }
    return min(representable, key=lambda value: (abs(value - target), value))


def _point_on_lattice_circle(
    center: tuple[int, int],
    radius_squared: int,
) -> tuple[int, int]:
    """Return one deterministic lattice point at the requested squared radius."""

    limit = int(ceil(radius_squared**0.5))
    offsets = sorted(
        (dx, dy)
        for dx in range(-limit, limit + 1)
        for dy in range(-limit, limit + 1)
        if dx * dx + dy * dy == radius_squared
    )
    if not offsets:
        raise RingGeometryError("ring radius has no lattice point")
    dx, dy = offsets[0]
    return center[0] + dx, center[1] + dy


def parse_ring_svg(svg_bytes: bytes) -> RingSvgGeometry:
    """Parse one nested annulus SVG and classify its circle alignment."""

    try:
        root = ElementTree.fromstring(svg_bytes)
    except ElementTree.ParseError as exc:
        raise RingGeometryError("ring SVG is not valid XML") from exc
    cell, min_grid_x, min_grid_y = _line_grid(root)
    circles = _circle_elements(root) or _circle_like_paths(root)
    unique_circles: list[tuple[float, float, float]] = []
    # Legacy source SVGs often repeat the same contour for fill and stroke with
    # a small sub-pixel offset. Treat those render-only copies as one circle.
    duplicate_tolerance = max(0.2, cell * 0.03)
    for circle in sorted(circles, key=lambda value: value[2], reverse=True):
        if any(
            max(
                abs(circle[0] - existing[0]),
                abs(circle[1] - existing[1]),
                abs(circle[2] - existing[2]),
            )
            <= duplicate_tolerance
            for existing in unique_circles
        ):
            continue
        unique_circles.append(circle)
    circles = unique_circles
    if len(circles) < 2:
        raise RingGeometryError("ring SVG has fewer than two circles")
    outer = circles[0]
    _require_circle_inside_view_box(outer, _view_box(root))
    inner = circles[1]
    center_distance = hypot(inner[0] - outer[0], inner[1] - outer[1])
    if center_distance + inner[2] > outer[2] + cell * 0.08:
        raise RingGeometryError("ring SVG circles are not nested")
    alignment = "concentric" if center_distance <= cell * 0.08 else "offset"
    outer_squared = _nearest_lattice_radius_squared(outer[2] / cell)
    inner_squared = _nearest_lattice_radius_squared(inner[2] / cell)
    if inner_squared >= outer_squared:
        raise RingGeometryError("ring SVG radii are invalid")
    center = (
        int(round((outer[0] - min_grid_x) / cell)),
        int(round((outer[1] - min_grid_y) / cell)),
    )
    inner_center = (
        int(round((inner[0] - min_grid_x) / cell)),
        int(round((inner[1] - min_grid_y) / cell)),
    )
    return RingSvgGeometry(
        center=center,
        inner_center=inner_center,
        alignment=alignment,
        outer_point=_point_on_lattice_circle(center, outer_squared),
        inner_point=_point_on_lattice_circle(inner_center, inner_squared),
        outer_radius_squared=outer_squared,
        inner_radius_squared=inner_squared,
        svg_center=(outer[0], outer[1]),
        svg_outer_radius=outer[2],
        svg_inner_radius=inner[2],
        grid_cell_size=cell,
    )
