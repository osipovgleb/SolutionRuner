"""Extract a graph curve and optional tangent from raster pixels."""

from __future__ import annotations

import math

import cv2
import numpy as np

from .graph_contrast_grid import (
    color_aware_curve_evidence,
    detect_grid,
    effective_darkness,
    grid_pixel_mask,
)
from .graph_contrast_models import GridModel, TraceResult, XInterval
from .graph_contrast_tangent import (
    _shifted,
    detect_marked_tangent_grid_points,
    detect_tangent_line,
    detect_vertical_tangency_guide,
    trace_curve_around_tangent,
)
from .graph_contrast_trace import (
    enforce_tangent_contact,
    smooth_and_simplify_curve,
    snap_curve_endpoints,
    trim_text_bridge_tails,
)


def dominant_curve_path(
    darkness: np.ndarray,
    grid: GridModel,
    *,
    minimum_span_cells: float,
    x_interval: XInterval | None = None,
    curve_evidence: np.ndarray | None = None,
    preserve_colored_grid_crossings: bool = False,
) -> tuple[np.ndarray, float]:
    """Trace the strongest smooth left-to-right path after suppressing the fitted grid."""
    vertical_lines = grid.vertical_lines()
    horizontal_lines = grid.horizontal_lines()
    left = max(0, math.floor(vertical_lines[0]))
    right = min(darkness.shape[1] - 1, math.ceil(vertical_lines[-1]))
    top = max(0, math.floor(horizontal_lines[0]))
    bottom = min(darkness.shape[0] - 1, math.ceil(horizontal_lines[-1]))
    if x_interval is not None:
        interval_left = grid.vertical_axis_x + x_interval.left * grid.vertical.step
        interval_right = grid.vertical_axis_x + x_interval.right * grid.vertical.step
        left = max(left, math.floor(min(interval_left, interval_right)))
        right = min(right, math.ceil(max(interval_left, interval_right)))
        if right <= left:
            raise ValueError("condition_x_interval_does_not_overlap_detected_grid")

    suppression = grid_pixel_mask(darkness.shape, grid)
    signal = darkness if curve_evidence is None else curve_evidence
    if preserve_colored_grid_crossings and curve_evidence is not None:
        suppression &= curve_evidence < 0.075
    cleaned = signal.astype(np.float32).copy()
    cleaned[suppression] = 0.0
    step = min(grid.vertical.step, grid.horizontal.step)
    sigma = max(0.55, min(2.4, step * 0.04))
    blurred = cv2.GaussianBlur(cleaned, (0, 0), sigmaX=sigma, sigmaY=sigma)

    evidence = 4.5 * blurred[top : bottom + 1, left : right + 1] - 0.22
    crop_suppression = suppression[top : bottom + 1, left : right + 1]
    evidence[crop_suppression] = -0.30
    height, width = evidence.shape

    max_delta = min(32, max(5, math.ceil(step * 0.70)))
    scale = 14.0 / max(4.0, step)
    previous = np.zeros(height, dtype=np.float32)
    back = np.full((width, height), 32767, dtype=np.int16)
    best_score = -math.inf
    best_x = 0
    best_y = 0

    for x_index in range(width):
        best_previous = np.full(height, -1e9, dtype=np.float32)
        best_delta = np.zeros(height, dtype=np.int16)
        for delta in range(-max_delta, max_delta + 1):
            shifted = _shifted(previous, delta, -1e9)
            penalty = 0.025 * abs(delta) * scale + 0.006 * delta * delta * scale * scale
            candidate = shifted - penalty
            take = candidate > best_previous
            best_previous[take] = candidate[take]
            best_delta[take] = delta

        restart = best_previous < 0.0
        current = evidence[:, x_index] + np.where(restart, 0.0, best_previous)
        back[x_index] = np.where(restart, 32767, best_delta).astype(np.int16)
        y_index = int(np.argmax(current))
        score = float(current[y_index])
        if score > best_score:
            best_score = score
            best_x = x_index
            best_y = y_index
        previous = current

    reversed_points: list[tuple[float, float]] = []
    x_index = best_x
    y_index = best_y
    while x_index >= 0:
        reversed_points.append((float(left + x_index), float(top + y_index)))
        delta = int(back[x_index, y_index])
        if delta == 32767:
            break
        y_index -= delta
        x_index -= 1
    points = np.asarray(reversed_points[::-1], dtype=np.float32)
    minimum_span = float(minimum_span_cells) * grid.vertical.step
    if len(points) < 2 or float(points[-1, 0] - points[0, 0]) < minimum_span:
        raise ValueError(
            f"dominant_curve_too_short: span={points[-1, 0] - points[0, 0]:.2f}px, "
            f"required={minimum_span:.2f}px"
        )
    return points, best_score


def extract_graph(
    rgba: np.ndarray,
    *,
    foreground_threshold: float = 0.20,
    grid_mask_radius: int | None = None,
    vertical_axis_x: float | None = None,
    horizontal_axis_y: float | None = None,
    minimum_span_cells: float = 3.0,
    snap_tolerance_cells: float = 0.22,
    smoothing_cells: float = 0.030,
    simplify_cells: float = 0.035,
    x_interval: XInterval | None = None,
) -> tuple[np.ndarray, GridModel, TraceResult]:
    """Run the complete deterministic raster-grid and dominant-curve extraction pipeline."""
    darkness = effective_darkness(rgba)
    grid = detect_grid(
        darkness,
        foreground_threshold=foreground_threshold,
        grid_mask_radius=grid_mask_radius,
        vertical_axis_x=vertical_axis_x,
        horizontal_axis_y=horizontal_axis_y,
    )
    curve_evidence, color_weighting_enabled, _ = color_aware_curve_evidence(
        rgba,
        darkness,
        grid,
    )
    raw_points, score = dominant_curve_path(
        darkness,
        grid,
        minimum_span_cells=minimum_span_cells,
        x_interval=x_interval,
        curve_evidence=curve_evidence,
        preserve_colored_grid_crossings=color_weighting_enabled,
    )
    curve_points, start_tail_trimmed, end_tail_trimmed = trim_text_bridge_tails(
        raw_points,
        grid,
    )
    points, start, end = snap_curve_endpoints(
        curve_points,
        grid,
        snap_tolerance_cells=snap_tolerance_cells,
        force_start_open=start_tail_trimmed
        or bool(x_interval and x_interval.left_open),
        force_end_open=end_tail_trimmed or bool(x_interval and x_interval.right_open),
    )
    smoothed, simplified = smooth_and_simplify_curve(
        points,
        grid,
        smoothing_cells=smoothing_cells,
        simplify_cells=simplify_cells,
    )
    return (
        darkness,
        grid,
        TraceResult(raw_points, smoothed, simplified, score, start, end),
    )


def extract_graph_with_tangent(
    rgba: np.ndarray,
    *,
    foreground_threshold: float = 0.20,
    grid_mask_radius: int | None = None,
    vertical_axis_x: float | None = None,
    horizontal_axis_y: float | None = None,
    snap_tolerance_cells: float = 0.22,
    smoothing_cells: float = 0.030,
    simplify_cells: float = 0.035,
) -> tuple[np.ndarray, GridModel, TraceResult]:
    """Extract a nonlinear function, its tangent, and the dashed ``x_0`` guide."""
    darkness = effective_darkness(rgba)
    grid = detect_grid(
        darkness,
        foreground_threshold=foreground_threshold,
        grid_mask_radius=grid_mask_radius,
        vertical_axis_x=vertical_axis_x,
        horizontal_axis_y=horizontal_axis_y,
    )
    tangent = detect_tangent_line(darkness, grid)
    vertical_guide = detect_vertical_tangency_guide(darkness, grid, tangent)
    tangent_markers = detect_marked_tangent_grid_points(
        darkness,
        grid,
        tangent,
        vertical_guide,
    )
    raw_points, score = trace_curve_around_tangent(
        darkness,
        grid,
        tangent,
        vertical_guide,
    )
    points, start, end = snap_curve_endpoints(
        raw_points,
        grid,
        snap_tolerance_cells=snap_tolerance_cells,
        snap_y_to_grid=False,
    )
    smoothed, simplified = smooth_and_simplify_curve(
        points,
        grid,
        smoothing_cells=smoothing_cells,
        simplify_cells=simplify_cells,
    )
    smoothed, simplified = enforce_tangent_contact(
        smoothed,
        grid,
        tangent,
        vertical_guide,
        simplify_cells=simplify_cells,
    )
    return (
        darkness,
        grid,
        TraceResult(
            raw_points,
            smoothed,
            simplified,
            score,
            start,
            end,
            tangent=tangent,
            vertical_guide=vertical_guide,
            tangent_markers=tangent_markers,
        ),
    )
