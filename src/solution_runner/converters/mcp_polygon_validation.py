"""Validate polygon conversion diagnostics and generated SVG assets."""

from __future__ import annotations

import ast
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__:
    from .mcp_polygon_models import CandidateRejected
else:
    from mcp_polygon_models import CandidateRejected


def _parse_diagnostics(path: Path) -> dict[str, Any]:
    """Parse the converter's key=value diagnostics using safe literals."""

    if not path.is_file():
        raise CandidateRejected("converter did not create diagnostics")
    parsed: dict[str, Any] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        key, separator, raw_value = raw_line.partition("=")
        if not separator:
            continue
        key = key.strip()
        value = raw_value.strip()
        try:
            parsed[key] = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            try:
                parsed[key] = float(value)
            except ValueError:
                parsed[key] = value
    return parsed


def _polygon_area(points: Sequence[tuple[float, float]]) -> float:
    """Return the absolute shoelace area of one simple polygon."""

    return (
        abs(
            sum(
                x1 * y2 - x2 * y1
                for (x1, y1), (x2, y2) in zip(points, (*points[1:], points[0]))
            )
        )
        / 2.0
    )


def _validate_quadrilateral(grid_indices, theme_title):
    """Check that a four-vertex polygon matches its requested theme."""
    edges = [
        (
            grid_indices[(index + 1) % 4][0] - grid_indices[index][0],
            grid_indices[(index + 1) % 4][1] - grid_indices[index][1],
        )
        for index in range(4)
    ]
    if theme_title == "Трапеция":
        opposite_parallel = (
            edges[0][0] * edges[2][1] - edges[0][1] * edges[2][0] == 0
            or edges[1][0] * edges[3][1] - edges[1][1] * edges[3][0] == 0
        )
        if not opposite_parallel:
            raise CandidateRejected("detected quadrilateral is not a trapezoid")
    if theme_title == "Ромб":
        squared_lengths = [dx * dx + dy * dy for dx, dy in edges]
        if len(set(squared_lengths)) != 1:
            raise CandidateRejected("detected quadrilateral is not a rhombus")


def _validate_diagnostics(
    diagnostics: dict[str, Any], *, theme_title: str, expected_vertices: int
) -> dict[str, Any]:
    """Fail closed when detected lattice or polygon invariants are implausible."""

    required = {
        "grid_source",
        "alpha_grid_x_step",
        "alpha_grid_y_step",
        "source_quad_before_snap",
        "source_quad_on_alpha_grid",
        "source_polygon_points",
        "grid_indices",
        "svg_size",
    }
    missing = sorted(required - diagnostics.keys())
    if missing:
        raise CandidateRejected(f"diagnostics are missing fields: {missing}")
    points_raw = diagnostics["source_polygon_points"]
    if not isinstance(points_raw, (list, tuple)):
        raise CandidateRejected("source_polygon_points is not a list")
    points = [tuple(map(int, point)) for point in points_raw]
    if len(points) != expected_vertices:
        raise CandidateRejected(
            f"detected {len(points)} vertices; theme requires {expected_vertices}"
        )
    if len(set(points)) != len(points):
        raise CandidateRejected("detected polygon has duplicate vertices")
    x_step = float(diagnostics["alpha_grid_x_step"])
    y_step = float(diagnostics["alpha_grid_y_step"])
    if min(x_step, y_step) <= 0:
        raise CandidateRejected("detected grid step is not positive")
    step_ratio = max(x_step, y_step) / min(x_step, y_step)
    if step_ratio > 1.18:
        raise CandidateRejected(
            f"square-grid step ratio is too large: {step_ratio:.4f}"
        )

    before = diagnostics["source_quad_before_snap"]
    snapped = diagnostics["source_quad_on_alpha_grid"]
    if len(before) != expected_vertices or len(snapped) != expected_vertices:
        raise CandidateRejected("snap diagnostics have the wrong vertex count")
    normalized_offsets = [
        max(abs(float(x1) - float(x2)) / x_step, abs(float(y1) - float(y2)) / y_step)
        for (x1, y1), (x2, y2) in zip(before, snapped)
    ]
    max_snap_offset = max(normalized_offsets, default=0.0)
    if max_snap_offset > 0.45:
        raise CandidateRejected(
            f"polygon-to-grid snap offset is too large: {max_snap_offset:.4f} cell"
        )
    grid_indices_raw = diagnostics["grid_indices"]
    if not isinstance(grid_indices_raw, (list, tuple)):
        raise CandidateRejected("grid_indices is not a list")
    grid_indices = [tuple(map(int, point)) for point in grid_indices_raw]
    if len(grid_indices) != expected_vertices or len(set(grid_indices)) != len(
        grid_indices
    ):
        raise CandidateRejected("ordered grid polygon has invalid vertices")
    area = _polygon_area(grid_indices)
    if area <= 0:
        raise CandidateRejected("detected polygon has zero area")
    if expected_vertices == 4:
        _validate_quadrilateral(grid_indices, theme_title)
    svg_size = diagnostics["svg_size"]
    if (
        not isinstance(svg_size, (list, tuple))
        or len(svg_size) != 2
        or min(float(svg_size[0]), float(svg_size[1])) <= 0
    ):
        raise CandidateRejected("generated SVG has invalid dimensions")
    return {
        "grid_source": str(diagnostics["grid_source"]),
        "grid_correction": str(diagnostics.get("grid_correction") or "none"),
        "vertices": points,
        "ordered_grid_vertices": grid_indices,
        "polygon_area_cells": area,
        "grid_step_ratio": step_ratio,
        "max_snap_offset_cells": max_snap_offset,
        "svg_size": list(svg_size),
    }


def _validate_svg(data: bytes, *, expected_vertices: int) -> None:
    """Validate generated SVG structure before server-side strict validation."""

    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise CandidateRejected(f"generated SVG is not valid XML: {exc}") from exc
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise CandidateRejected("generated XML root is not svg")
    if not root.get("viewBox"):
        raise CandidateRejected("generated SVG has no viewBox")
    blocked_tags = {"script", "foreignobject", "iframe", "object", "embed"}
    polygons = []
    for element in root.iter():
        local_tag = element.tag.rsplit("}", 1)[-1].lower()
        if local_tag in blocked_tags:
            raise CandidateRejected(f"generated SVG contains blocked tag {local_tag}")
        for attribute, value in element.attrib.items():
            local_attribute = attribute.rsplit("}", 1)[-1].lower()
            lowered = str(value).strip().lower()
            if local_attribute.startswith("on"):
                raise CandidateRejected("generated SVG contains an event handler")
            if local_attribute in {"href", "src"} and lowered:
                raise CandidateRejected("generated SVG contains a resource reference")
            if "javascript:" in lowered:
                raise CandidateRejected("generated SVG contains a javascript URL")
        if local_tag == "polygon" and element.get("points"):
            polygons.append(element.get("points", ""))
    if not polygons:
        raise CandidateRejected("generated SVG contains no polygon")
    point_count = len(polygons[-1].replace(",", " ").split()) // 2
    if point_count != expected_vertices:
        raise CandidateRejected(
            f"generated SVG polygon has {point_count} points, expected {expected_vertices}"
        )
