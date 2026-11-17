"""Render traced graphs with their tangent and construction lines."""

from __future__ import annotations

import html
import math

import numpy as np

from .graph_contrast_models import GridModel, TangentLine, TraceResult, VerticalGuide
from .graph_contrast_paths import _cubic_path, _fmt, _polyline_path
from .graph_contrast_svg import _map_points_to_svg, _smooth_function_spline_path


def _logical_canvas_bounds(
    grid: GridModel,
    pad_cells: int,
) -> tuple[float, float, float, float]:
    """Return logical ``x_min, x_max, y_min, y_max`` for the SVG canvas."""
    vertical_count = len(grid.vertical_lines())
    horizontal_count = len(grid.horizontal_lines())
    columns = (vertical_count - 1) + 2 * pad_cells
    rows = (horizontal_count - 1) + 2 * pad_cells
    x_min = (
        grid.vertical_lines()[0] - grid.vertical_axis_x
    ) / grid.vertical.step - pad_cells
    x_max = x_min + columns
    y_max = (
        grid.horizontal_axis_y - grid.horizontal_lines()[0]
    ) / grid.horizontal.step + pad_cells
    y_min = y_max - rows
    return float(x_min), float(x_max), float(y_min), float(y_max)


def _logical_points_to_svg(
    points: np.ndarray,
    bounds: tuple[float, float, float, float],
    cell_size: float,
) -> np.ndarray:
    """Map logical Cartesian points into a normalized SVG viewport."""
    x_min, _, _, y_max = bounds
    mapped = np.empty_like(points, dtype=np.float64)
    mapped[:, 0] = (points[:, 0] - x_min) * cell_size
    mapped[:, 1] = (y_max - points[:, 1]) * cell_size
    return mapped


def _clip_tangent_to_logical_canvas(
    tangent: TangentLine,
    bounds: tuple[float, float, float, float],
) -> np.ndarray:
    """Clip the mathematically infinite tangent to the SVG canvas rectangle."""
    x_min, x_max, y_min, y_max = bounds
    slope = tangent.logical_slope
    intercept = tangent.logical_intercept
    candidates: list[tuple[float, float]] = []
    for logical_x in (x_min, x_max):
        logical_y = slope * logical_x + intercept
        if y_min - 1e-8 <= logical_y <= y_max + 1e-8:
            candidates.append((logical_x, logical_y))
    if abs(slope) > 1e-10:
        for logical_y in (y_min, y_max):
            logical_x = (logical_y - intercept) / slope
            if x_min - 1e-8 <= logical_x <= x_max + 1e-8:
                candidates.append((logical_x, logical_y))
    unique: list[tuple[float, float]] = []
    for candidate in candidates:
        if not any(math.dist(candidate, existing) <= 1e-7 for existing in unique):
            unique.append(candidate)
    if len(unique) < 2:
        raise ValueError("tangent_does_not_cross_svg_canvas")
    first, second = max(
        (
            (left, right)
            for left_index, left in enumerate(unique)
            for right in unique[left_index + 1 :]
        ),
        key=lambda pair: math.dist(pair[0], pair[1]),
    )
    return np.asarray([first, second], dtype=np.float64)


def _tangent_lattice_markers(
    tangent: TangentLine,
    grid: GridModel,
    guide: VerticalGuide,
    bounds: tuple[float, float, float, float],
) -> np.ndarray:
    """Choose one exact grid intersection on each side of the tangency point."""
    x_min, x_max, y_min, y_max = bounds
    logical_x_0 = (guide.pixel_x - grid.vertical_axis_x) / grid.vertical.step
    candidates: list[tuple[float, float]] = []
    for integer_x in range(math.ceil(x_min), math.floor(x_max) + 1):
        logical_y = tangent.logical_slope * integer_x + tangent.logical_intercept
        integer_y = round(logical_y)
        if abs(logical_y - integer_y) <= 1e-7 and y_min <= integer_y <= y_max:
            candidates.append((float(integer_x), float(integer_y)))
    minimum_distance = 1.15
    left = [point for point in candidates if point[0] <= logical_x_0 - minimum_distance]
    right = [
        point for point in candidates if point[0] >= logical_x_0 + minimum_distance
    ]
    if left and right:
        return np.asarray(
            [
                max(left, key=lambda point: point[0]),
                min(right, key=lambda point: point[0]),
            ],
            dtype=np.float64,
        )
    if len(candidates) >= 2:
        return np.asarray([candidates[0], candidates[-1]], dtype=np.float64)
    return np.empty((0, 2), dtype=np.float64)


def _curve_path_for_tangent(grid, trace, path_mode, cell_size, pad_cells):
    guide = trace.vertical_guide
    tangent = trace.tangent
    mapped_trace = _map_points_to_svg(
        trace.points if path_mode == "bezier" else trace.simplified_points,
        grid,
        cell_size=cell_size,
        pad_cells=pad_cells,
    )
    if path_mode == "bezier":
        mapped_contact_geometry = _map_points_to_svg(
            np.asarray(
                [
                    [guide.pixel_x, guide.end_y],
                    [guide.pixel_x + 1.0, tangent.y_at(guide.pixel_x + 1.0)],
                ],
                dtype=np.float32,
            ),
            grid,
            cell_size=cell_size,
            pad_cells=pad_cells,
        )
        curve_path, _ = _smooth_function_spline_path(
            mapped_trace,
            mapped_contact_geometry[0],
            mapped_contact_geometry[1] - mapped_contact_geometry[0],
            cell_size,
        )
    elif path_mode == "cubic":
        curve_path = _cubic_path(mapped_trace)
    else:
        curve_path = _polyline_path(mapped_trace)

    return curve_path


def _tangent_labels(geometry, end_svg, x_axis_guide_svg, names, include_labels):
    axis_x, axis_y, width, height, cell_size = geometry
    escaped_graph_label, escaped_guide_label, curve_color = names
    labels = ""
    ticks = ""
    if include_labels:
        tick_half = max(2.5, cell_size * 0.15)
        unit_x = axis_x + cell_size
        unit_y = axis_y - cell_size
        ticks = (
            f'<path d="M{_fmt(unit_x)} {_fmt(axis_y - tick_half)}V{_fmt(axis_y + tick_half)} '
            f'M{_fmt(axis_x - tick_half)} {_fmt(unit_y)}H{_fmt(axis_x + tick_half)}"/>'
        )
        if float(end_svg[0]) + 75.0 <= width:
            curve_label_x = float(end_svg[0]) + 7.0
            curve_label_y = float(end_svg[1]) + 5.0
        else:
            curve_label_x = max(4.0, float(end_svg[0]) - 72.0)
            curve_label_y = max(15.0, float(end_svg[1]) - 8.0)
        curve_label_y = min(height - 5.0, curve_label_y)
        labels = (
            '<g fill="#111" font-family="Times New Roman, Times, serif" font-size="12.5">'
            f'<text x="{_fmt(axis_x + 5)}" y="{_fmt(axis_y + 16)}">0</text>'
            f'<text x="{_fmt(unit_x - 3)}" y="{_fmt(axis_y + 16)}">1</text>'
            f'<text x="{_fmt(axis_x + 5)}" y="{_fmt(unit_y + 4)}">1</text>'
            f'<text x="{_fmt(width - 11)}" y="{_fmt(axis_y + 17)}" font-size="15" '
            'font-style="italic">x</text>'
            f'<text x="{_fmt(axis_x - 13)}" y="15" font-size="15" font-style="italic">y</text>'
            f'<text x="{_fmt(x_axis_guide_svg[0] - 7)}" y="{_fmt(x_axis_guide_svg[1] - 9)}" '
            f'font-style="italic">{escaped_guide_label}</text>'
            f'<text x="{_fmt(curve_label_x)}" y="{_fmt(curve_label_y)}" fill="{curve_color}" '
            f'font-style="italic">{escaped_graph_label}</text>'
            "</g>"
        )

    return labels, ticks


def _tangent_geometry(grid, trace, cell_size, pad_cells):
    tangent, guide = trace.tangent, trace.vertical_guide
    logical_bounds = _logical_canvas_bounds(grid, pad_cells)
    tangent_logical = _clip_tangent_to_logical_canvas(tangent, logical_bounds)
    tangent_svg = _logical_points_to_svg(tangent_logical, logical_bounds, cell_size)
    logical_x_0 = (guide.pixel_x - grid.vertical_axis_x) / grid.vertical.step
    logical_y_0 = tangent.logical_slope * logical_x_0 + tangent.logical_intercept
    guide_logical = np.asarray(
        [[logical_x_0, 0.0], [logical_x_0, logical_y_0]],
        dtype=np.float64,
    )
    guide_svg = _logical_points_to_svg(guide_logical, logical_bounds, cell_size)
    lattice_logical = (
        trace.tangent_markers
        if trace.tangent_markers is not None
        else _tangent_lattice_markers(tangent, grid, guide, logical_bounds)
    )
    lattice_svg = (
        _logical_points_to_svg(
            lattice_logical,
            logical_bounds,
            cell_size,
        )
        if len(lattice_logical)
        else np.empty((0, 2), dtype=np.float64)
    )
    tangency_svg = guide_svg[1]
    x_axis_guide_svg = guide_svg[0]
    return tangent_svg, guide_svg, lattice_svg, tangency_svg, x_axis_guide_svg


def render_graph_with_tangent_svg(
    grid: GridModel,
    trace: TraceResult,
    *,
    cell_size: float,
    pad_cells: int,
    path_mode: str,
    bezier_error_cells: float,
    endpoint_style: str,
    include_labels: bool,
    curve_color: str,
    graph_label: str,
) -> str:
    """Render a function curve, a separately fitted tangent, and its ``x_0`` guide."""
    if trace.tangent is None or trace.vertical_guide is None:
        raise ValueError("tangent_renderer_requires_tangent_and_vertical_guide")
    guide = trace.vertical_guide
    pad_cells = max(0, int(pad_cells))
    vertical_count = len(grid.vertical_lines())
    horizontal_count = len(grid.horizontal_lines())
    columns = (vertical_count - 1) + 2 * pad_cells
    rows = (horizontal_count - 1) + 2 * pad_cells
    width = columns * cell_size
    height = rows * cell_size
    vertical_grid_x = [index * cell_size for index in range(columns + 1)]
    horizontal_grid_y = [index * cell_size for index in range(rows + 1)]
    grid_path = " ".join(
        [f"M{_fmt(x)} 0V{_fmt(height)}" for x in vertical_grid_x]
        + [f"M0 {_fmt(y)}H{_fmt(width)}" for y in horizontal_grid_y]
    )

    first_x = grid.vertical_lines()[0]
    first_y = grid.horizontal_lines()[0]
    axis_x = (
        (grid.vertical_axis_x - first_x) / grid.vertical.step + pad_cells
    ) * cell_size
    axis_y = (
        (grid.horizontal_axis_y - first_y) / grid.horizontal.step + pad_cells
    ) * cell_size
    curve_path = _curve_path_for_tangent(grid, trace, path_mode, cell_size, pad_cells)

    tangent_svg, guide_svg, lattice_svg, tangency_svg, x_axis_guide_svg = (
        _tangent_geometry(grid, trace, cell_size, pad_cells)
    )
    end_svg = _map_points_to_svg(
        np.asarray([[trace.end.pixel_x, trace.end.pixel_y]], dtype=np.float32),
        grid,
        cell_size=cell_size,
        pad_cells=pad_cells,
    )[0]

    escaped_graph_label = html.escape(graph_label)
    escaped_guide_label = html.escape(guide.label)
    labels, ticks = _tangent_labels(
        (axis_x, axis_y, width, height, cell_size),
        end_svg,
        x_axis_guide_svg,
        (escaped_graph_label, escaped_guide_label, curve_color),
        include_labels,
    )

    tangent_marker_nodes = "".join(
        f'<circle cx="{_fmt(point[0])}" cy="{_fmt(point[1])}" r="2.35" fill="#0a990a"/>'
        for point in lattice_svg
    )
    tangent_marker_nodes += (
        f'<circle cx="{_fmt(tangency_svg[0])}" cy="{_fmt(tangency_svg[1])}" '
        f'r="2.35" fill="{curve_color}"/>'
        f'<circle cx="{_fmt(x_axis_guide_svg[0])}" cy="{_fmt(x_axis_guide_svg[1])}" '
        'r="1.42" fill="#111"/>'
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(width)}" height="{_fmt(height)}"
     viewBox="0 0 {_fmt(width)} {_fmt(height)}" role="img" aria-labelledby="title desc">
  <title id="title">График {escaped_graph_label} и касательная</title>
  <desc id="desc">Восстановленные координатная сетка, график функции, касательная и направляющая x₀.</desc>
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"
            markerUnits="strokeWidth"><path d="M0 0L8 4L0 8L2.3 4Z" fill="#111"/></marker>
  </defs>
  <path d="{grid_path}" fill="none" stroke="#adadad" stroke-width="0.75"/>
  <g fill="none" stroke="#111" stroke-width="1.15">
    <path d="M0 {_fmt(axis_y)}H{_fmt(max(0, width - 5))}" marker-end="url(#arrow)"/>
    <path d="M{_fmt(axis_x)} {_fmt(height)}V5" marker-end="url(#arrow)"/>
    {ticks}
  </g>
  {labels}
  <path d="M{_fmt(tangent_svg[0, 0])} {_fmt(tangent_svg[0, 1])} L{_fmt(tangent_svg[1, 0])} {_fmt(tangent_svg[1, 1])}"
        fill="none" stroke="#0a990a" stroke-width="1.25" stroke-linecap="round"/>
  <path d="M{_fmt(guide_svg[0, 0])} {_fmt(guide_svg[0, 1])} L{_fmt(guide_svg[1, 0])} {_fmt(guide_svg[1, 1])}"
        fill="none" stroke="#111" stroke-width="1" stroke-dasharray="7.5 3"/>
  <path d="{curve_path}" fill="none" stroke="{curve_color}" stroke-width="1.55"
        stroke-linecap="round" stroke-linejoin="round"/>
  <g>{tangent_marker_nodes}</g>
</svg>
'''
