"""Detect tangent lines and trace curves around their contact point."""

from __future__ import annotations

import math
from fractions import Fraction

import cv2
import numpy as np

from .graph_contrast_grid import grid_pixel_mask
from .graph_contrast_models import GridModel, TangentLine, VerticalGuide


def _shifted(values: np.ndarray, delta: int, fill: float) -> np.ndarray:
    """Shift a one-dimensional array without wraparound."""
    shifted = np.full(values.shape, fill, dtype=values.dtype)
    if delta > 0:
        shifted[delta:] = values[:-delta]
    elif delta < 0:
        shifted[:delta] = values[-delta:]
    else:
        shifted[:] = values
    return shifted


def _snap_tangent_to_grid(grid, slope, intercept):
    """Snap a tangent to a nearby simple rational line when it stays close."""
    raw_logical_slope = -slope * grid.vertical.step / grid.horizontal.step
    raw_logical_intercept = (
        grid.horizontal_axis_y - (slope * grid.vertical_axis_x + intercept)
    ) / grid.horizontal.step
    rational_slope = Fraction(float(raw_logical_slope)).limit_denominator(8)
    logical_slope = float(raw_logical_slope)
    logical_intercept = float(raw_logical_intercept)
    if abs(float(rational_slope) - raw_logical_slope) <= 0.035:
        snapped_slope = float(rational_slope)
        snapped_intercept = (
            round(raw_logical_intercept * rational_slope.denominator)
            / rational_slope.denominator
        )
        maximum_shift = max(
            abs(
                (snapped_slope * logical_x + snapped_intercept)
                - (raw_logical_slope * logical_x + raw_logical_intercept)
            )
            for logical_x in (-4.0, 0.0, 4.0)
        )
        if maximum_shift <= 0.20:
            logical_slope = snapped_slope
            logical_intercept = snapped_intercept
            slope = -logical_slope * grid.horizontal.step / grid.vertical.step
            intercept = (
                grid.horizontal_axis_y
                - logical_intercept * grid.horizontal.step
                - slope * grid.vertical_axis_x
            )
    return slope, intercept, logical_slope, logical_intercept


def detect_tangent_line(darkness: np.ndarray, grid: GridModel) -> TangentLine:
    """Detect and robustly fit the longest non-axis straight stroke."""
    grid_mask = grid_pixel_mask(darkness.shape, grid)
    threshold = max(0.18, grid.detection_threshold * 1.35)
    binary = ((darkness >= threshold) & ~grid_mask).astype(np.uint8) * 255
    step = min(grid.vertical.step, grid.horizontal.step)
    detected = cv2.HoughLinesP(
        binary,
        rho=1.0,
        theta=np.pi / 720.0,
        threshold=max(12, round(step * 1.25)),
        minLineLength=max(18, round(step * 2.8)),
        maxLineGap=max(3, round(step * 0.45)),
    )
    if detected is None:
        raise ValueError("tangent_line_not_found")

    candidates: list[tuple[float, float, int, int, int, int]] = []
    for raw_line in np.asarray(detected).reshape(-1, 4):
        x_1, y_1, x_2, y_2 = map(int, raw_line)
        delta_x = x_2 - x_1
        delta_y = y_2 - y_1
        if abs(delta_x) < max(2.0, step * 0.35):
            continue
        slope = delta_y / delta_x
        if not 0.05 <= abs(slope) <= 8.0:
            continue
        length = math.hypot(delta_x, delta_y)
        candidates.append((length, -abs(slope), x_1, y_1, x_2, y_2))
    if not candidates:
        raise ValueError("non_axis_tangent_line_not_found")

    _, _, x_1, y_1, x_2, y_2 = max(candidates)
    slope = float((y_2 - y_1) / (x_2 - x_1))
    intercept = float(y_1 - slope * x_1)
    foreground_y, foreground_x = np.nonzero(
        (darkness >= max(0.15, grid.detection_threshold * 1.15)) & ~grid_mask
    )
    fitting_band = max(2.2, step * 0.20)
    selected = np.zeros(foreground_x.shape, dtype=bool)
    for _ in range(3):
        distance = np.abs(
            slope * foreground_x.astype(np.float64)
            - foreground_y.astype(np.float64)
            + intercept
        ) / math.sqrt(slope * slope + 1.0)
        selected = distance <= fitting_band
        if int(selected.sum()) < max(20, round(step * 2.0)):
            break
        x_values = foreground_x[selected].astype(np.float64)
        y_values = foreground_y[selected].astype(np.float64)
        weights = darkness[foreground_y[selected], foreground_x[selected]].astype(
            np.float64
        )
        design = np.column_stack([x_values, np.ones(len(x_values), dtype=np.float64)])
        weighted_design = design * np.sqrt(weights)[:, None]
        weighted_y = y_values * np.sqrt(weights)
        slope, intercept = map(
            float,
            np.linalg.lstsq(weighted_design, weighted_y, rcond=None)[0],
        )

    support_x = foreground_x[selected]
    if support_x.size < 2:
        raise ValueError("tangent_line_support_too_small")
    start_x = float(max(0, int(support_x.min())))
    end_x = float(min(darkness.shape[1] - 1, int(support_x.max())))
    if end_x - start_x < step * 2.5:
        raise ValueError("tangent_line_span_too_short")
    slope, intercept, logical_slope, logical_intercept = _snap_tangent_to_grid(
        grid, slope, intercept
    )
    return TangentLine(
        slope=slope,
        intercept=intercept,
        start_x=start_x,
        end_x=end_x,
        logical_slope=float(logical_slope),
        logical_intercept=float(logical_intercept),
        support_pixels=int(selected.sum()),
    )


def detect_vertical_tangency_guide(
    darkness: np.ndarray,
    grid: GridModel,
    tangent: TangentLine,
) -> VerticalGuide:
    """Detect the dashed ``x_0`` guide that terminates on the tangent."""
    grid_mask = grid_pixel_mask(darkness.shape, grid)
    threshold = max(0.18, grid.detection_threshold * 1.35)
    binary = ((darkness >= threshold) & ~grid_mask).astype(np.uint8) * 255
    step = min(grid.vertical.step, grid.horizontal.step)
    detected = cv2.HoughLinesP(
        binary,
        rho=1.0,
        theta=np.pi / 720.0,
        threshold=max(10, round(step * 0.90)),
        minLineLength=max(10, round(step * 1.25)),
        maxLineGap=max(3, round(step * 0.45)),
    )
    if detected is None:
        raise ValueError("tangency_vertical_guide_not_found")

    candidates: list[tuple[float, float, float, float]] = []
    vertical_grid_lines = grid.vertical_lines()
    for raw_line in np.asarray(detected).reshape(-1, 4):
        x_1, y_1, x_2, y_2 = map(float, raw_line)
        if abs(x_2 - x_1) > max(2.0, step * 0.18):
            continue
        length = abs(y_2 - y_1)
        if length < step * 1.20:
            continue
        pixel_x = (x_1 + x_2) / 2.0
        if min(abs(pixel_x - line) for line in vertical_grid_lines) < step * 0.22:
            continue
        segment_top = min(y_1, y_2)
        segment_bottom = max(y_1, y_2)
        tangent_y = tangent.y_at(pixel_x)
        axis_y = grid.horizontal_axis_y
        tangent_distance = max(segment_top - tangent_y, tangent_y - segment_bottom, 0.0)
        axis_distance = max(segment_top - axis_y, axis_y - segment_bottom, 0.0)
        if tangent_distance > step * 0.75 or axis_distance > step * 0.75:
            continue
        candidates.append((length, pixel_x, segment_top, segment_bottom))
    if not candidates:
        raise ValueError("x0_vertical_guide_not_found")

    _, seed_x, _, _ = max(candidates)
    band = np.abs(np.arange(darkness.shape[1], dtype=np.float64) - seed_x) <= 1.5
    selected_y, selected_x = np.nonzero(
        (darkness >= max(0.15, grid.detection_threshold * 1.15))
        & ~grid_mask
        & band[None, :]
    )
    tangent_y = tangent.y_at(seed_x)
    guide_top = min(grid.horizontal_axis_y, tangent_y)
    guide_bottom = max(grid.horizontal_axis_y, tangent_y)
    near_seed = (selected_y >= guide_top - step * 0.20) & (
        selected_y <= guide_bottom + step * 0.20
    )
    if int(near_seed.sum()) >= 8:
        weights = darkness[selected_y[near_seed], selected_x[near_seed]].astype(
            np.float64
        )
        pixel_x = float(np.average(selected_x[near_seed], weights=weights))
    else:
        pixel_x = float(seed_x)
    end_y = float(tangent.y_at(pixel_x))
    return VerticalGuide(
        pixel_x=pixel_x,
        start_y=float(grid.horizontal_axis_y),
        end_y=end_y,
    )


def detect_marked_tangent_grid_points(
    darkness: np.ndarray,
    grid: GridModel,
    tangent: TangentLine,
    guide: VerticalGuide,
) -> np.ndarray:
    """Return the actual filled lattice markers visible on the raster tangent."""
    height, width = darkness.shape
    step = min(grid.vertical.step, grid.horizontal.step)
    logical_x_0 = (guide.pixel_x - grid.vertical_axis_x) / grid.vertical.step
    logical_x_min = (0.0 - grid.vertical_axis_x) / grid.vertical.step
    logical_x_max = (float(width - 1) - grid.vertical_axis_x) / grid.vertical.step
    yy, xx = np.indices(darkness.shape, dtype=np.float64)
    tangent_distance = np.abs(tangent.slope * xx - yy + tangent.intercept) / math.sqrt(
        tangent.slope * tangent.slope + 1.0
    )
    radius = max(3.0, step * 0.34)
    dark_threshold = max(0.50, grid.detection_threshold * 2.25)
    minimum_dark_pixels = max(5, round(step * 0.35))
    scored: list[tuple[float, float, float]] = []

    for integer_x in range(math.ceil(logical_x_min), math.floor(logical_x_max) + 1):
        logical_y = tangent.logical_slope * integer_x + tangent.logical_intercept
        integer_y = round(logical_y)
        if abs(logical_y - integer_y) > 1e-7:
            continue
        if abs(float(integer_x) - logical_x_0) < 0.85:
            # The nonlinear curve thickens the tangency region; it is rendered
            # separately as the blue contact point, never as a green marker.
            continue
        pixel_x = grid.vertical_axis_x + integer_x * grid.vertical.step
        pixel_y = grid.horizontal_axis_y - integer_y * grid.horizontal.step
        if not (
            radius <= pixel_x < width - radius and radius <= pixel_y < height - radius
        ):
            continue
        disk = np.square(xx - pixel_x) + np.square(yy - pixel_y) <= radius * radius
        dark = disk & (darkness >= dark_threshold)
        dark_count = int(dark.sum())
        outside_line_count = int((dark & (tangent_distance > 1.0)).sum())
        if dark_count < minimum_dark_pixels or outside_line_count < 1:
            continue
        score = float(dark_count) + 0.5 * float(outside_line_count)
        scored.append((score, float(integer_x), float(integer_y)))

    selected = sorted(scored, key=lambda item: (-item[0], item[1]))[:2]
    selected.sort(key=lambda item: item[1])
    return np.asarray(
        [[logical_x, logical_y] for _, logical_x, logical_y in selected],
        dtype=np.float64,
    ).reshape(-1, 2)


def _anchored_curve_direction(
    evidence: np.ndarray,
    grid: GridModel,
    *,
    anchor_x: int,
    anchor_y: int,
    direction: int,
) -> tuple[np.ndarray, float]:
    """Trace one curve branch from a fixed tangency point until evidence ends."""
    if direction not in {-1, 1}:
        raise ValueError("trace_direction_must_be_minus_or_plus_one")
    height, width = evidence.shape
    x_values = list(range(anchor_x, width if direction > 0 else -1, direction))
    step = min(grid.vertical.step, grid.horizontal.step)
    max_delta = min(32, max(5, math.ceil(step * 0.70)))
    scale = 14.0 / max(4.0, step)
    previous = np.full(height, -1e9, dtype=np.float32)
    previous[int(np.clip(anchor_y, 0, height - 1))] = 0.0
    back_steps: list[np.ndarray] = []
    last_supported_index = 0
    last_supported_y = int(np.clip(anchor_y, 0, height - 1))
    last_supported_score = 0.0
    unsupported_columns = 0
    maximum_gap = max(7, round(step * 0.70))

    for path_index, pixel_x in enumerate(x_values[1:], start=1):
        best_previous = np.full(height, -1e9, dtype=np.float32)
        best_delta = np.zeros(height, dtype=np.int16)
        for delta in range(-max_delta, max_delta + 1):
            shifted = _shifted(previous, delta, -1e9)
            penalty = 0.025 * abs(delta) * scale + 0.006 * delta * delta * scale * scale
            candidate = shifted - penalty
            take = candidate > best_previous
            best_previous[take] = candidate[take]
            best_delta[take] = delta
        current = evidence[:, pixel_x] + best_previous
        pixel_y = int(np.argmax(current))
        back_steps.append(best_delta)
        local_start = max(0, pixel_y - 2)
        local_end = min(height, pixel_y + 3)
        local_evidence = float(
            evidence[local_start:local_end, pixel_x].max(initial=-1.0)
        )
        if local_evidence > 0.02:
            last_supported_index = path_index
            last_supported_y = pixel_y
            last_supported_score = float(current[pixel_y])
            unsupported_columns = 0
        else:
            unsupported_columns += 1
        previous = current
        if unsupported_columns >= maximum_gap and path_index >= round(step):
            break

    pixel_y = last_supported_y
    reversed_points: list[tuple[float, float]] = [
        (float(x_values[last_supported_index]), float(pixel_y))
    ]
    for path_index in range(last_supported_index, 0, -1):
        delta = int(back_steps[path_index - 1][pixel_y])
        pixel_y -= delta
        reversed_points.append((float(x_values[path_index - 1]), float(pixel_y)))
    points = np.asarray(reversed_points[::-1], dtype=np.float32)
    if direction < 0:
        points = points[::-1].copy()
    return points, last_supported_score


def trace_curve_around_tangent(
    darkness: np.ndarray,
    grid: GridModel,
    tangent: TangentLine,
    guide: VerticalGuide,
) -> tuple[np.ndarray, float]:
    """Trace only the nonlinear function curve on both sides of tangency."""
    step = min(grid.vertical.step, grid.horizontal.step)
    yy, xx = np.indices(darkness.shape, dtype=np.float32)
    tangent_distance = np.abs(tangent.slope * xx - yy + tangent.intercept) / math.sqrt(
        tangent.slope * tangent.slope + 1.0
    )
    contact_window = step * 0.65
    tangent_mask = (tangent_distance <= max(2.5, step * 0.23)) & (
        np.abs(xx - guide.pixel_x) > contact_window
    )
    guide_top = min(guide.start_y, guide.end_y)
    guide_bottom = max(guide.start_y, guide.end_y)
    guide_mask = (
        (np.abs(xx - guide.pixel_x) <= max(1.5, step * 0.16))
        & (yy >= guide_top - 1.0)
        & (yy <= guide_bottom + 1.0)
        & (np.abs(yy - guide.end_y) >= 2.0)
    )
    suppression = grid_pixel_mask(darkness.shape, grid) | tangent_mask | guide_mask
    cleaned = darkness.astype(np.float32).copy()
    cleaned[suppression] = 0.0
    sigma = max(0.55, min(2.4, step * 0.04))
    blurred = cv2.GaussianBlur(cleaned, (0, 0), sigmaX=sigma, sigmaY=sigma)
    evidence = 4.5 * blurred - 0.22
    evidence[suppression] = -0.30

    anchor_x = round(guide.pixel_x)
    anchor_y = round(guide.end_y)
    left_points, left_score = _anchored_curve_direction(
        evidence,
        grid,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        direction=-1,
    )
    right_points, right_score = _anchored_curve_direction(
        evidence,
        grid,
        anchor_x=anchor_x,
        anchor_y=anchor_y,
        direction=1,
    )
    if len(left_points) < 2 or len(right_points) < 2:
        raise ValueError("tangent_curve_branch_too_short")
    points = np.vstack([left_points, right_points[1:]])
    if float(points[-1, 0] - points[0, 0]) < step * 2.5:
        raise ValueError("tangent_curve_span_too_short")
    return points, left_score + right_score
