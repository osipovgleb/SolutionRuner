"""Infer graph labels and render the traced curve as SVG."""

from __future__ import annotations

import html
import math
import re

import numpy as np
from scipy.interpolate import UnivariateSpline

from .graph_contrast_models import Endpoint, GridModel, TraceResult, XInterval
from .graph_contrast_paths import (
    _bezier_path,
    _bezier_path_with_fixed_tangent,
    _cubic_path,
    _fmt,
    _polyline_path,
    _unit_vector,
)


def _coordinate_label(value: float) -> str:
    """Format a logical coordinate and use a mathematical minus sign."""
    nearest_integer = round(value)
    if abs(value - nearest_integer) <= 0.16:
        text = str(int(nearest_integer))
    else:
        text = _fmt(value, 1)
    return text.replace("-", "−")


def infer_graph_kind(
    condition_text: str | None, explicit_kind: str | None = None
) -> str:
    """Choose the isolated extractor whose visual objects match the condition."""
    if explicit_kind and explicit_kind != "auto":
        return explicit_kind
    normalized = (condition_text or "").lower().replace("\u00ad", "")
    if "касательн" in normalized and "график" in normalized:
        return "function_with_tangent"
    return "single_curve"


def infer_graph_label(
    condition_text: str | None,
    explicit_label: str | None = None,
) -> str:
    """Infer a mathematical graph label from condition semantics, with an explicit override."""
    if explicit_label is not None and explicit_label.strip():
        return explicit_label.strip()
    normalized = (condition_text or "").lower().replace("\u00ad", "")
    normalized = re.sub(r"[\u00a0\u202f\s]+", " ", normalized).strip()
    if re.search(r"график (?:второй|2[ -]?й) производн", normalized):
        return "y = f″(x)"
    if re.search(r"график производн", normalized):
        return "y = f′(x)"
    if re.search(r"график первообразн", normalized):
        return "y = F(x)"
    return "y = f(x)"


def infer_x_interval(condition_text: str | None) -> XInterval | None:
    """Extract a numeric x-interval from condition text when one is explicitly present."""
    normalized = (condition_text or "").replace("\u00ad", "")
    normalized = normalized.replace("−", "-").replace("–", "-")
    normalized = re.sub(r"[\u00a0\u202f\s]+", " ", normalized)
    pattern = re.compile(
        r"([\[(])\s*([+-]?\d+(?:[.,]\d+)?)\s*[;,]\s*"
        r"([+-]?\d+(?:[.,]\d+)?)\s*([\])])"
    )
    matches = list(pattern.finditer(normalized))
    if not matches:
        return None
    selected = matches[0]
    for match in matches:
        prefix = normalized[max(0, match.start() - 80) : match.start()].lower()
        if "интервал" in prefix or "отрез" in prefix or "промежут" in prefix:
            selected = match
            break
    left = float(selected.group(2).replace(",", "."))
    right = float(selected.group(3).replace(",", "."))
    if right <= left:
        return None
    return XInterval(
        left=left,
        right=right,
        left_open=selected.group(1) == "(",
        right_open=selected.group(4) == ")",
    )


def _map_points_to_svg(
    points: np.ndarray,
    grid: GridModel,
    *,
    cell_size: float,
    pad_cells: int,
) -> np.ndarray:
    """Map source pixels to the normalized SVG canvas."""
    first_x = grid.vertical_lines()[0]
    first_y = grid.horizontal_lines()[0]
    mapped = np.empty_like(points, dtype=np.float64)
    mapped[:, 0] = (
        (points[:, 0] - first_x) / grid.vertical.step + pad_cells
    ) * cell_size
    mapped[:, 1] = (
        (points[:, 1] - first_y) / grid.horizontal.step + pad_cells
    ) * cell_size
    return mapped


def _smooth_function_spline_path(
    points: np.ndarray,
    anchor: np.ndarray,
    forward_tangent: np.ndarray,
    cell_size: float,
) -> tuple[str, int]:
    """Render one globally smooth function spline with exact contact geometry."""
    fitting_points = points[
        np.concatenate([[True], np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9])
    ].astype(np.float64)
    direction = _unit_vector(forward_tangent)
    if len(fitting_points) < 5 or not np.any(direction) or abs(direction[0]) <= 1e-9:
        return _bezier_path_with_fixed_tangent(
            fitting_points,
            anchor,
            forward_tangent,
            maximum_error=max(0.6, cell_size * 0.03),
        )

    x_values = fitting_points[:, 0]
    y_values = fitting_points[:, 1]
    residual_tolerance = max(0.8, cell_size * 0.06)
    spline = UnivariateSpline(
        x_values,
        y_values,
        k=3,
        s=len(fitting_points) * residual_tolerance * residual_tolerance,
        ext=3,
    )
    derivative = spline.derivative()
    anchor_x = float(anchor[0])
    target_slope = float(direction[1] / direction[0])
    value_delta = float(anchor[1] - spline(anchor_x))
    slope_delta = float(target_slope - derivative(anchor_x))
    contact_sigma = max(3.0, cell_size * 0.42)

    def corrected_values(sample_x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Evaluate the smooth fit and its analytic first derivative."""
        offsets = sample_x - anchor_x
        influence = np.exp(-0.5 * np.square(offsets / contact_sigma))
        linear = value_delta + slope_delta * offsets
        correction = linear * influence
        correction_derivative = influence * (
            slope_delta - linear * offsets / (contact_sigma * contact_sigma)
        )
        return (
            np.asarray(spline(sample_x), dtype=np.float64) + correction,
            np.asarray(derivative(sample_x), dtype=np.float64) + correction_derivative,
        )

    # Match the visually successful long-segment graph style: roughly one
    # cubic per grid cell.  Shorter uniform segments preserve raster stair-step
    # changes so faithfully that the result reads as a rounded polyline.
    interval = max(8.0, cell_size)
    interval_count = max(2, math.ceil((x_values[-1] - x_values[0]) / interval))
    node_x = np.linspace(x_values[0], x_values[-1], interval_count + 1)
    node_x = np.unique(np.concatenate([node_x, np.asarray([anchor_x])]))
    node_y, node_slope = corrected_values(node_x)
    node_y[0] = y_values[0]
    node_y[-1] = y_values[-1]
    endpoint_sample_size = min(8, len(fitting_points))
    node_slope[0] = float(
        np.polyfit(
            x_values[:endpoint_sample_size],
            y_values[:endpoint_sample_size],
            1,
        )[0]
    )
    node_slope[-1] = float(
        np.polyfit(
            x_values[-endpoint_sample_size:],
            y_values[-endpoint_sample_size:],
            1,
        )[0]
    )

    commands = [f"M{_fmt(node_x[0])} {_fmt(node_y[0])}"]
    for index in range(len(node_x) - 1):
        delta_x = float(node_x[index + 1] - node_x[index])
        control_1 = (
            node_x[index] + delta_x / 3.0,
            node_y[index] + node_slope[index] * delta_x / 3.0,
        )
        control_2 = (
            node_x[index + 1] - delta_x / 3.0,
            node_y[index + 1] - node_slope[index + 1] * delta_x / 3.0,
        )
        commands.append(
            "C"
            f"{_fmt(control_1[0])} {_fmt(control_1[1])} "
            f"{_fmt(control_2[0])} {_fmt(control_2[1])} "
            f"{_fmt(node_x[index + 1])} {_fmt(node_y[index + 1])}"
        )
    return " ".join(commands), len(node_x) - 1


def _endpoint_circle_svg(
    endpoint: Endpoint,
    mapped_point: np.ndarray,
    *,
    endpoint_style: str,
    curve_color: str,
) -> str:
    """Render one endpoint circle according to the requested or detected style."""
    style = endpoint_style
    if style == "auto":
        style = "open" if endpoint.looks_open else "none"
    if style == "none":
        return ""
    fill = "#fff" if style == "open" else curve_color
    return (
        f'<circle cx="{_fmt(mapped_point[0])}" cy="{_fmt(mapped_point[1])}" r="2.55" '
        f'fill="{fill}" stroke="{curve_color}" stroke-width="1.1"/>'
    )


def _axis_labels(trace, axis, endpoints, cell_size, escaped_graph_label):
    """Render coordinate ticks and labels for the normalized curve."""
    axis_x, axis_y, width = axis
    start_svg, end_svg = endpoints
    unit_y = axis_y - cell_size
    tick_half = max(2.5, cell_size * 0.15)
    ticks = (
        f'<path d="M{_fmt(start_svg[0])} {_fmt(axis_y - tick_half)}V{_fmt(axis_y + tick_half)} '
        f"M{_fmt(end_svg[0])} {_fmt(axis_y - tick_half)}V{_fmt(axis_y + tick_half)} "
        f'M{_fmt(axis_x - tick_half)} {_fmt(unit_y)}H{_fmt(axis_x + tick_half)}"/>'
    )
    labels = (
        '<g fill="#111" font-family="Times New Roman, Times, serif" font-size="12.5">'
        f'<text x="{_fmt(start_svg[0] - 7)}" y="{_fmt(axis_y + 16)}">'
        f"{_coordinate_label(trace.start.logical_x)}</text>"
        f'<text x="{_fmt(end_svg[0] - 4)}" y="{_fmt(axis_y + 16)}">'
        f"{_coordinate_label(trace.end.logical_x)}</text>"
        f'<text x="{_fmt(axis_x + 5)}" y="{_fmt(unit_y + 4)}">1</text>'
        f'<text x="{_fmt(axis_x + 5)}" y="{_fmt(axis_y + 16)}">0</text>'
        f'<text x="{_fmt(width - 11)}" y="{_fmt(axis_y + 17)}" font-size="15" '
        'font-style="italic">x</text>'
        f'<text x="{_fmt(axis_x - 13)}" y="15" font-size="15" font-style="italic">y</text>'
        f'<text x="{_fmt(max(4, width - 88))}" y="15" font-size="13" '
        f'font-style="italic">{escaped_graph_label}</text>'
        "</g>"
    )

    return labels, ticks


def _curve_geometry(grid, trace, cell_size, pad_cells, path_options):
    """Map the curve and its endpoint markers onto the SVG canvas."""
    path_mode, bezier_error_cells = path_options
    mapped_points = _map_points_to_svg(
        trace.simplified_points,
        grid,
        cell_size=cell_size,
        pad_cells=pad_cells,
    )
    if path_mode == "bezier":
        mapped_trace = _map_points_to_svg(
            trace.points,
            grid,
            cell_size=cell_size,
            pad_cells=pad_cells,
        )
        curve_path, _ = _bezier_path(mapped_trace, bezier_error_cells * cell_size)
    elif path_mode == "cubic":
        curve_path = _cubic_path(mapped_points)
    else:
        curve_path = _polyline_path(mapped_points)

    start_svg = _map_points_to_svg(
        np.asarray([[trace.start.pixel_x, trace.start.pixel_y]], dtype=np.float32),
        grid,
        cell_size=cell_size,
        pad_cells=pad_cells,
    )[0]
    end_svg = _map_points_to_svg(
        np.asarray([[trace.end.pixel_x, trace.end.pixel_y]], dtype=np.float32),
        grid,
        cell_size=cell_size,
        pad_cells=pad_cells,
    )[0]

    return curve_path, start_svg, end_svg


def render_svg(
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
    """Render a normalized SVG grid, axes, labels, and traced function curve."""
    pad_cells = max(0, int(pad_cells))
    vertical_count = len(grid.vertical_lines())
    horizontal_count = len(grid.horizontal_lines())
    columns = (vertical_count - 1) + 2 * pad_cells
    rows = (horizontal_count - 1) + 2 * pad_cells
    width = columns * cell_size
    height = rows * cell_size

    grid_path = " ".join(
        [f"M{_fmt(index * cell_size)} 0V{_fmt(height)}" for index in range(columns + 1)]
        + [f"M0 {_fmt(index * cell_size)}H{_fmt(width)}" for index in range(rows + 1)]
    )

    first_x = grid.vertical_lines()[0]
    first_y = grid.horizontal_lines()[0]
    axis_x = (
        (grid.vertical_axis_x - first_x) / grid.vertical.step + pad_cells
    ) * cell_size
    axis_y = (
        (grid.horizontal_axis_y - first_y) / grid.horizontal.step + pad_cells
    ) * cell_size
    curve_path, start_svg, end_svg = _curve_geometry(
        grid, trace, cell_size, pad_cells, (path_mode, bezier_error_cells)
    )

    escaped_graph_label = html.escape(graph_label)
    labels, ticks = ("", "")
    if include_labels:
        labels, ticks = _axis_labels(
            trace,
            (axis_x, axis_y, width),
            (start_svg, end_svg),
            cell_size,
            escaped_graph_label,
        )

    endpoint_nodes = "".join(
        [
            _endpoint_circle_svg(
                trace.start,
                start_svg,
                endpoint_style=endpoint_style,
                curve_color=curve_color,
            ),
            _endpoint_circle_svg(
                trace.end,
                end_svg,
                endpoint_style=endpoint_style,
                curve_color=curve_color,
            ),
        ]
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{_fmt(width)}" height="{_fmt(height)}"
     viewBox="0 0 {_fmt(width)} {_fmt(height)}" role="img" aria-labelledby="title desc">
  <title id="title">График {escaped_graph_label}</title>
  <desc id="desc">Детерминированно восстановленные координатная сетка и график функции.</desc>
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
  <path d="{curve_path}" fill="none" stroke="{curve_color}" stroke-width="1.55"
        stroke-linecap="round" stroke-linejoin="round"/>
  <g>{endpoint_nodes}</g>
</svg>
'''
