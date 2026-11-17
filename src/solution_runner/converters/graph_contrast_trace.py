"""Clean and align traced curves with the detected grid and tangent."""

from __future__ import annotations

import cv2
import numpy as np

from .graph_contrast_models import Endpoint, GridModel, TangentLine, VerticalGuide


def _nearest(value: float, candidates: tuple[float, ...]) -> float:
    """Return the nearest value with deterministic tie-breaking."""
    return float(
        min(candidates, key=lambda candidate: (abs(candidate - value), candidate))
    )


def _logical_point(
    pixel_x: float, pixel_y: float, grid: GridModel
) -> tuple[float, float]:
    """Convert source pixels to logical Cartesian coordinates."""
    return (
        (pixel_x - grid.vertical_axis_x) / grid.vertical.step,
        (grid.horizontal_axis_y - pixel_y) / grid.horizontal.step,
    )


def _large_jump_runs(jumps: np.ndarray, threshold: float) -> list[tuple[int, int]]:
    """Return inclusive runs of adjacent vertical jumps above a threshold."""
    indices = np.flatnonzero(jumps >= threshold)
    if indices.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = previous = int(indices[0])
    for raw_index in indices[1:]:
        index = int(raw_index)
        if index == previous + 1:
            previous = index
            continue
        runs.append((start, previous))
        start = previous = index
    runs.append((start, previous))
    return runs


def trim_text_bridge_tails(
    points: np.ndarray,
    grid: GridModel,
) -> tuple[np.ndarray, bool, bool]:
    """Remove flat text tails connected to the curve by repeated near-limit jumps."""
    if len(points) < 10:
        return points, False, False

    jumps = np.abs(np.diff(points[:, 1]))
    jump_threshold = max(4.0, grid.horizontal.step * 0.52)
    window = min(len(jumps), max(8, round(grid.vertical.step * 1.5)))
    flat_tolerance = max(2.0, grid.horizontal.step * 0.22)
    start_cut = 0
    end_cut = len(points)
    start_trimmed = False
    end_trimmed = False

    for run_start, run_end in _large_jump_runs(jumps[:window], jump_threshold):
        run_length = run_end - run_start + 1
        prefix = points[: run_start + 1, 1]
        if (
            run_length >= 2
            and len(prefix) >= 3
            and float(np.ptp(prefix)) <= flat_tolerance
        ):
            start_cut = run_end + 1
            start_trimmed = True

    offset = len(jumps) - window
    for local_start, local_end in _large_jump_runs(jumps[-window:], jump_threshold):
        run_start = offset + local_start
        run_end = offset + local_end
        run_length = run_end - run_start + 1
        suffix = points[run_end + 1 :, 1]
        if (
            run_length >= 2
            and len(suffix) >= 3
            and float(np.ptp(suffix)) <= flat_tolerance
        ):
            end_cut = run_start + 1
            end_trimmed = True
            break

    if end_cut - start_cut < 2:
        return points, False, False
    return points[start_cut:end_cut].copy(), start_trimmed, end_trimmed


def _interpolate_or_extrapolate_y(points: np.ndarray, pixel_x: float) -> float:
    """Evaluate trace y at x, using a short endpoint regression outside its span."""
    if points[0, 0] <= pixel_x <= points[-1, 0]:
        return float(np.interp(pixel_x, points[:, 0], points[:, 1]))
    sample_size = min(5, len(points))
    sample = points[:sample_size] if pixel_x < points[0, 0] else points[-sample_size:]
    design = np.column_stack([sample[:, 0], np.ones(sample_size, dtype=np.float32)])
    slope, intercept = np.linalg.lstsq(design, sample[:, 1], rcond=None)[0]
    return float(slope * pixel_x + intercept)


def _endpoint(
    pixel_x: float,
    pixel_y: float,
    grid: GridModel,
    *,
    looks_open: bool,
) -> Endpoint:
    """Build an endpoint with both pixel and logical coordinates."""
    logical_x, logical_y = _logical_point(pixel_x, pixel_y, grid)
    return Endpoint(pixel_x, pixel_y, logical_x, logical_y, looks_open)


def snap_curve_endpoints(
    raw_points: np.ndarray,
    grid: GridModel,
    *,
    snap_tolerance_cells: float,
    snap_y_to_grid: bool = True,
    force_start_open: bool = False,
    force_end_open: bool = False,
) -> tuple[np.ndarray, Endpoint, Endpoint]:
    """Snap endpoint centers to nearby grid lines and identify open-circle overhangs."""
    points = raw_points.copy()
    vertical_lines = grid.vertical_lines()
    horizontal_lines = grid.horizontal_lines()
    x_tolerance = max(1.0, snap_tolerance_cells * grid.vertical.step)
    y_tolerance = max(1.0, snap_tolerance_cells * grid.horizontal.step)

    raw_start_x, _raw_start_y = map(float, points[0])
    raw_end_x, _raw_end_y = map(float, points[-1])
    start_x_line = _nearest(raw_start_x, vertical_lines)
    end_x_line = _nearest(raw_end_x, vertical_lines)
    start_x = (
        start_x_line if abs(start_x_line - raw_start_x) <= x_tolerance else raw_start_x
    )
    end_x = end_x_line if abs(end_x_line - raw_end_x) <= x_tolerance else raw_end_x

    start_y = _interpolate_or_extrapolate_y(points, start_x)
    end_y = _interpolate_or_extrapolate_y(points, end_x)
    start_y_line = _nearest(start_y, horizontal_lines)
    end_y_line = _nearest(end_y, horizontal_lines)
    if snap_y_to_grid and abs(start_y_line - start_y) <= y_tolerance:
        start_y = start_y_line
    if snap_y_to_grid and abs(end_y_line - end_y) <= y_tolerance:
        end_y = end_y_line

    open_overhang = max(1.35, grid.vertical.step * 0.075)
    start_open = force_start_open or start_x - raw_start_x >= open_overhang
    end_open = force_end_open or raw_end_x - end_x >= open_overhang

    points = points[(points[:, 0] >= start_x) & (points[:, 0] <= end_x)]
    if len(points) < 2:
        raise ValueError("curve_disappeared_after_endpoint_snapping")
    points[0] = (start_x, start_y)
    points[-1] = (end_x, end_y)
    return (
        points,
        _endpoint(start_x, start_y, grid, looks_open=start_open),
        _endpoint(end_x, end_y, grid, looks_open=end_open),
    )


def smooth_and_simplify_curve(
    points: np.ndarray,
    grid: GridModel,
    *,
    smoothing_cells: float,
    simplify_cells: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth pixel jitter and reduce the trace to stable curve knots."""
    smoothed = points.astype(np.float32).copy()
    sigma = max(0.0, smoothing_cells * grid.vertical.step)
    if sigma > 0.0 and len(smoothed) >= 5:
        smoothed[:, 1] = cv2.GaussianBlur(
            smoothed[:, 1].reshape(1, -1),
            (0, 0),
            sigmaX=sigma,
        ).reshape(-1)
        smoothed[0] = points[0]
        smoothed[-1] = points[-1]

    epsilon = max(0.05, simplify_cells * min(grid.vertical.step, grid.horizontal.step))
    simplified = cv2.approxPolyDP(smoothed.reshape(-1, 1, 2), epsilon, False).reshape(
        -1, 2
    )
    simplified[0] = smoothed[0]
    simplified[-1] = smoothed[-1]
    return smoothed, simplified


def enforce_tangent_contact(
    points: np.ndarray,
    grid: GridModel,
    tangent: TangentLine,
    guide: VerticalGuide,
    *,
    simplify_cells: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Locally constrain a smoothed curve to the detected tangent value and slope."""
    adjusted = points.astype(np.float32).copy()
    anchor_x = float(guide.pixel_x)
    anchor_y = float(guide.end_y)
    current_y = float(np.interp(anchor_x, adjusted[:, 0], adjusted[:, 1]))
    slope_radius = max(2.0, grid.vertical.step * 0.28)
    slope_sample = np.abs(adjusted[:, 0] - anchor_x) <= slope_radius
    if int(slope_sample.sum()) >= 3:
        sample = adjusted[slope_sample].astype(np.float64)
        design = np.column_stack([sample[:, 0], np.ones(len(sample), dtype=np.float64)])
        current_slope = float(np.linalg.lstsq(design, sample[:, 1], rcond=None)[0][0])
    else:
        anchor_index = int(np.argmin(np.abs(adjusted[:, 0] - anchor_x)))
        left_index = max(0, anchor_index - 1)
        right_index = min(len(adjusted) - 1, anchor_index + 1)
        current_slope = float(
            (adjusted[right_index, 1] - adjusted[left_index, 1])
            / max(1e-6, adjusted[right_index, 0] - adjusted[left_index, 0])
        )

    influence_sigma = max(3.0, grid.vertical.step * 0.52)
    offsets = adjusted[:, 0].astype(np.float64) - anchor_x
    influence = np.exp(-0.5 * np.square(offsets / influence_sigma))
    correction = (
        anchor_y - current_y + (tangent.slope - current_slope) * offsets
    ) * influence
    adjusted[:, 1] += correction.astype(np.float32)
    adjusted[0] = points[0]
    adjusted[-1] = points[-1]

    epsilon = max(0.05, simplify_cells * min(grid.vertical.step, grid.horizontal.step))
    simplified = cv2.approxPolyDP(
        adjusted.reshape(-1, 1, 2),
        epsilon,
        False,
    ).reshape(-1, 2)
    simplified[0] = adjusted[0]
    simplified[-1] = adjusted[-1]
    return adjusted, simplified
