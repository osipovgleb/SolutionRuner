#!/usr/bin/env python3
"""Deterministically recover a Cartesian grid and a dominant function curve from a raster image."""

from __future__ import annotations

import argparse
import html
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import UnivariateSpline

from .png_to_svg_by_contrast import extract_id, load_image


@dataclass(frozen=True)
class GridAxisModel:
    """Describe one fitted family of regularly spaced grid lines."""

    observed: tuple[float, ...]
    origin: float
    step: float
    max_residual: float

    def lines(
        self,
        lower_bound: float | None = None,
        upper_bound: float | None = None,
    ) -> tuple[float, ...]:
        """Return fitted lattice lines across observations or optional image bounds."""
        if (lower_bound is None) != (upper_bound is None):
            raise ValueError("grid_line_bounds_must_be_provided_together")
        if lower_bound is None or upper_bound is None:
            indices = [int(round((value - self.origin) / self.step)) for value in self.observed]
            first = min(indices)
            last = max(indices)
        else:
            tolerance = max(1.0, self.max_residual + 0.25)
            first = int(math.ceil((lower_bound - tolerance - self.origin) / self.step))
            last = int(math.floor((upper_bound + tolerance - self.origin) / self.step))
        return tuple(self.origin + index * self.step for index in range(first, last + 1))


@dataclass(frozen=True)
class GridModel:
    """Hold the fitted grid and the pixel positions of the two coordinate axes."""

    vertical: GridAxisModel
    horizontal: GridAxisModel
    vertical_axis_x: float
    horizontal_axis_y: float
    grid_mask_radius: int
    detection_threshold: float
    image_width: int
    image_height: int

    def vertical_lines(self) -> tuple[float, ...]:
        """Return the vertical lattice extrapolated across the source image."""
        return self.vertical.lines(0.0, float(self.image_width - 1))

    def horizontal_lines(self) -> tuple[float, ...]:
        """Return the horizontal lattice extrapolated across the source image."""
        return self.horizontal.lines(0.0, float(self.image_height - 1))


@dataclass(frozen=True)
class XInterval:
    """Describe the logical x-domain and whether its endpoint markers are open."""

    left: float
    right: float
    left_open: bool
    right_open: bool


@dataclass(frozen=True)
class Endpoint:
    """Describe a traced curve endpoint in source pixels and logical grid coordinates."""

    pixel_x: float
    pixel_y: float
    logical_x: float
    logical_y: float
    looks_open: bool


@dataclass(frozen=True)
class TangentLine:
    """Describe a detected straight tangent in source-pixel coordinates."""

    slope: float
    intercept: float
    start_x: float
    end_x: float
    logical_slope: float
    logical_intercept: float
    support_pixels: int

    def y_at(self, pixel_x: float) -> float:
        """Evaluate the fitted tangent at one source-pixel x coordinate."""
        return self.slope * pixel_x + self.intercept


@dataclass(frozen=True)
class VerticalGuide:
    """Describe the dashed vertical guide from the x-axis to tangency."""

    pixel_x: float
    # ``start_y`` is always the x-axis and ``end_y`` is always tangency.  They
    # are intentionally not sorted: a tangent may lie above or below the axis.
    start_y: float
    end_y: float
    label: str = "x₀"


@dataclass(frozen=True)
class TraceResult:
    """Contain the dominant curve trace and its deterministic dynamic-programming score."""

    raw_points: np.ndarray
    points: np.ndarray
    simplified_points: np.ndarray
    score: float
    start: Endpoint
    end: Endpoint
    tangent: TangentLine | None = None
    vertical_guide: VerticalGuide | None = None
    tangent_markers: np.ndarray | None = None


def effective_darkness(rgba: np.ndarray) -> np.ndarray:
    """Return visible luminance/chroma contrast in ``[0, 1]`` against the background."""
    rgb = rgba[:, :, :3].astype(np.float32) / 255.0
    alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    luminance = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    border = np.concatenate([rgb[0], rgb[-1], rgb[:, 0], rgb[:, -1]], axis=0)
    background = np.percentile(border, 90.0, axis=0).astype(np.float32)
    background_luminance = float(
        0.299 * background[0] + 0.587 * background[1] + 0.114 * background[2]
    )
    luminance_contrast = np.abs(background_luminance - luminance)
    chroma_contrast = np.linalg.norm(rgb - background, axis=2) / math.sqrt(3.0)
    visible_contrast = np.maximum(luminance_contrast, chroma_contrast * 0.90) * alpha
    return np.clip(visible_contrast, 0.0, 1.0)


def color_aware_curve_evidence(
    rgba: np.ndarray,
    darkness: np.ndarray,
    grid: GridModel,
) -> tuple[np.ndarray, bool, float]:
    """Downweight neutral labels and axes when a chromatic curve is present."""
    rgb = rgba[:, :, :3].astype(np.uint8)
    saturation = (
        cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[:, :, 1].astype(np.float32) / 255.0
    )
    suppression = grid_pixel_mask(darkness.shape, grid)
    candidate_threshold = max(0.18, grid.detection_threshold * 1.50)
    candidates = (darkness >= candidate_threshold) & ~suppression
    if int(candidates.sum()) < 64:
        return darkness, False, 0.0

    candidate_saturation = saturation[candidates]
    saturation_reference = float(np.percentile(candidate_saturation, 75.0))
    chromatic_fraction = float(np.mean(candidate_saturation >= 0.12))
    if saturation_reference < 0.18 or chromatic_fraction < 0.18:
        return darkness, False, saturation_reference

    neutral_floor = 0.035
    normalized_saturation = np.clip(
        (saturation - neutral_floor) / max(0.08, saturation_reference - neutral_floor),
        0.0,
        1.0,
    )
    color_weight = 0.08 + 0.92 * normalized_saturation
    return np.clip(darkness * color_weight, 0.0, 1.0), True, saturation_reference


def _group_adjacent(values: np.ndarray, max_gap: int = 3) -> list[list[int]]:
    """Group sorted integer coordinates separated by at most ``max_gap`` pixels."""
    if values.size == 0:
        return []
    groups: list[list[int]] = [[int(values[0])]]
    for raw_value in values[1:]:
        value = int(raw_value)
        if value - groups[-1][-1] <= max_gap:
            groups[-1].append(value)
        else:
            groups.append([value])
    return groups


def projection_line_centers(
    darkness: np.ndarray,
    *,
    vertical: bool,
    foreground_threshold: float,
) -> list[float]:
    """Find long vertical or horizontal foreground bands from a contrast projection."""
    foreground = darkness >= float(foreground_threshold)
    projection_axis = 0 if vertical else 1
    coverage = foreground.sum(axis=projection_axis).astype(np.float64)
    strength = darkness.sum(axis=projection_axis).astype(np.float64)
    orthogonal_span = foreground.shape[0] if vertical else foreground.shape[1]
    peak = float(coverage.max(initial=0.0))
    if peak <= 0.0:
        return []

    cutoff = max(6.0, orthogonal_span * 0.14, peak * 0.32)
    selected = np.flatnonzero(coverage >= cutoff)
    centers: list[float] = []
    for group in _group_adjacent(selected):
        weights = strength[group]
        if float(weights.sum()) <= 0.0:
            continue
        centers.append(float(np.average(np.asarray(group, dtype=np.float64), weights=weights)))
    return centers


def _step_candidates(values: np.ndarray, axis_size: int) -> list[float]:
    """Generate stable grid-step candidates from all pairwise line distances."""
    min_step = max(4.0, float(axis_size) * 0.012)
    max_step = max(min_step, float(axis_size) * 0.35)
    candidates: list[float] = []
    for left_index in range(len(values)):
        for right_index in range(left_index + 1, len(values)):
            distance = float(values[right_index] - values[left_index])
            if distance < min_step:
                continue
            max_divisor = min(16, max(1, int(math.floor(distance / min_step))))
            for divisor in range(1, max_divisor + 1):
                candidate = distance / divisor
                if min_step <= candidate <= max_step:
                    candidates.append(candidate)
    if not candidates:
        return []

    bin_width = max(0.25, float(axis_size) * 0.001)
    bins = Counter(int(round(candidate / bin_width)) for candidate in candidates)
    return [key * bin_width for key, _ in bins.most_common(80)]


def fit_grid_axis(
    centers: list[float],
    axis_size: int,
    preferred_step: float | None = None,
) -> GridAxisModel:
    """Fit a regular one-dimensional lattice while rejecting missing-line subharmonics."""
    if len(centers) < 4:
        raise ValueError(f"not_enough_grid_lines: found {len(centers)}, need at least 4")

    values = np.asarray(sorted(centers), dtype=np.float64)
    candidates = _step_candidates(values, axis_size)
    if preferred_step is not None:
        candidates = [
            candidate
            for candidate in candidates
            if preferred_step * 0.72 <= candidate <= preferred_step * 1.28
        ] or [float(preferred_step)]
    if not candidates:
        raise ValueError("grid_step_not_found")

    best: tuple[tuple[float, ...], float, dict[int, tuple[float, float]]] | None = None
    for candidate in candidates:
        tolerance = max(1.25, candidate * 0.09)
        for phase in values:
            lattice = np.rint((values - phase) / candidate).astype(int)
            residuals = np.abs(values - (phase + lattice * candidate))
            matched: dict[int, tuple[float, float]] = {}
            for value, index, residual in zip(values, lattice, residuals):
                if residual > tolerance:
                    continue
                current = matched.get(int(index))
                if current is None or residual < current[1]:
                    matched[int(index)] = (float(value), float(residual))
            if len(matched) < 4:
                continue
            lattice_span = max(matched) - min(matched) + 1
            coverage = len(matched) / max(1, lattice_span)
            mean_residual = sum(item[1] for item in matched.values()) / len(matched)
            score = (
                float(len(matched)),
                float(coverage),
                -float(mean_residual / candidate),
                float(candidate),
            )
            if best is None or score > best[0]:
                best = (score, candidate, matched)

    if best is None:
        raise ValueError("grid_phase_not_found")

    _, _, matched = best
    lattice = np.asarray(sorted(matched), dtype=np.float64)
    matched_values = np.asarray([matched[int(index)][0] for index in lattice], dtype=np.float64)
    design = np.column_stack([np.ones_like(lattice), lattice])
    origin, step = np.linalg.lstsq(design, matched_values, rcond=None)[0]
    if step <= 0.0:
        raise ValueError("invalid_grid_step")

    first_index = int(round((float(values.min()) - origin) / step))
    origin += first_index * step
    normalized_indices = np.rint((matched_values - origin) / step).astype(int)
    residuals = np.abs(matched_values - (origin + normalized_indices * step))
    return GridAxisModel(
        observed=tuple(float(value) for value in values),
        origin=float(origin),
        step=float(step),
        max_residual=float(residuals.max(initial=0.0)),
    )


def _line_strength(
    darkness: np.ndarray,
    coordinate: float,
    *,
    vertical: bool,
    plot_min: float,
    plot_max: float,
) -> float:
    """Score a fitted line, giving extra weight to axis extensions outside the grid."""
    index = int(round(coordinate))
    if vertical:
        if not 0 <= index < darkness.shape[1]:
            return -math.inf
        profile = darkness[:, max(0, index - 1) : min(darkness.shape[1], index + 2)].max(axis=1)
    else:
        if not 0 <= index < darkness.shape[0]:
            return -math.inf
        profile = darkness[max(0, index - 1) : min(darkness.shape[0], index + 2), :].max(axis=0)

    lower = max(0, int(math.floor(plot_min)))
    upper = min(len(profile), int(math.ceil(plot_max)) + 1)
    inside = float(profile[lower:upper].sum())
    outside = float(profile[:lower].sum() + profile[upper:].sum())
    return inside + 2.5 * outside


def _detect_axis_line(
    darkness: np.ndarray,
    candidates: tuple[float, ...],
    *,
    vertical: bool,
    plot_min: float,
    plot_max: float,
) -> float:
    """Choose the darkest fitted grid line, including its arrow extension, as an axis."""
    scored = [
        (
            _line_strength(
                darkness,
                candidate,
                vertical=vertical,
                plot_min=plot_min,
                plot_max=plot_max,
            ),
            candidate,
        )
        for candidate in candidates
    ]
    if not scored:
        raise ValueError("axis_candidates_not_found")
    return float(max(scored, key=lambda item: (item[0], -abs(item[1])))[1])


def detect_grid(
    darkness: np.ndarray,
    *,
    foreground_threshold: float,
    grid_mask_radius: int | None,
    vertical_axis_x: float | None,
    horizontal_axis_y: float | None,
) -> GridModel:
    """Detect the regular Cartesian grid and its horizontal and vertical axes."""
    thresholds = [float(foreground_threshold)]
    thresholds.extend(
        threshold
        for threshold in (0.18, 0.16, 0.14, 0.12, 0.10, 0.08, 0.06, 0.04)
        if threshold < foreground_threshold and threshold not in thresholds
    )
    vertical: GridAxisModel | None = None
    horizontal: GridAxisModel | None = None
    detection_threshold = thresholds[-1]
    last_error: ValueError | None = None
    for threshold in thresholds:
        vertical_centers = projection_line_centers(
            darkness,
            vertical=True,
            foreground_threshold=threshold,
        )
        horizontal_centers = projection_line_centers(
            darkness,
            vertical=False,
            foreground_threshold=threshold,
        )
        try:
            candidate_vertical = fit_grid_axis(vertical_centers, darkness.shape[1])
            candidate_horizontal = fit_grid_axis(horizontal_centers, darkness.shape[0])
        except ValueError as error:
            last_error = error
            continue

        smaller = min(candidate_vertical.step, candidate_horizontal.step)
        larger = max(candidate_vertical.step, candidate_horizontal.step)
        ratio = larger / smaller
        multiple = int(round(ratio))
        if multiple in {2, 3, 4} and abs(ratio - multiple) <= 0.22:
            if candidate_vertical.step < candidate_horizontal.step:
                candidate_vertical = fit_grid_axis(
                    vertical_centers,
                    darkness.shape[1],
                    candidate_horizontal.step,
                )
            else:
                candidate_horizontal = fit_grid_axis(
                    horizontal_centers,
                    darkness.shape[0],
                    candidate_vertical.step,
                )

        final_ratio = max(candidate_vertical.step, candidate_horizontal.step) / min(
            candidate_vertical.step,
            candidate_horizontal.step,
        )
        if final_ratio > 1.35:
            last_error = ValueError(f"grid_step_ratio_not_square_enough: {final_ratio:.3f}")
            continue
        vertical = candidate_vertical
        horizontal = candidate_horizontal
        detection_threshold = threshold
        break

    if vertical is None or horizontal is None:
        raise last_error or ValueError("grid_not_found_at_any_contrast_threshold")

    vertical_lines = vertical.lines(0.0, float(darkness.shape[1] - 1))
    horizontal_lines = horizontal.lines(0.0, float(darkness.shape[0] - 1))
    detected_vertical_axis_x = _detect_axis_line(
        darkness,
        vertical_lines,
        vertical=True,
        plot_min=horizontal_lines[0],
        plot_max=horizontal_lines[-1],
    )
    detected_horizontal_axis_y = _detect_axis_line(
        darkness,
        horizontal_lines,
        vertical=False,
        plot_min=vertical_lines[0],
        plot_max=vertical_lines[-1],
    )

    radius = (
        max(0, int(round(min(vertical.step, horizontal.step) * 0.025)))
        if grid_mask_radius is None
        else max(0, int(grid_mask_radius))
    )
    return GridModel(
        vertical=vertical,
        horizontal=horizontal,
        vertical_axis_x=float(
            detected_vertical_axis_x if vertical_axis_x is None else vertical_axis_x
        ),
        horizontal_axis_y=float(
            detected_horizontal_axis_y if horizontal_axis_y is None else horizontal_axis_y
        ),
        grid_mask_radius=radius,
        detection_threshold=float(detection_threshold),
        image_width=int(darkness.shape[1]),
        image_height=int(darkness.shape[0]),
    )


def grid_pixel_mask(shape: tuple[int, int], grid: GridModel) -> np.ndarray:
    """Return a mask covering fitted grid and axis pixels that must not attract the trace."""
    height, width = shape
    yy, xx = np.ogrid[:height, :width]
    radius = float(grid.grid_mask_radius) + 0.51
    mask = np.zeros((height, width), dtype=bool)
    for coordinate in grid.vertical_lines():
        mask |= np.abs(xx - coordinate) <= radius
    for coordinate in grid.horizontal_lines():
        mask |= np.abs(yy - coordinate) <= radius
    return mask


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
    left = max(0, int(math.floor(vertical_lines[0])))
    right = min(darkness.shape[1] - 1, int(math.ceil(vertical_lines[-1])))
    top = max(0, int(math.floor(horizontal_lines[0])))
    bottom = min(darkness.shape[0] - 1, int(math.ceil(horizontal_lines[-1])))
    if x_interval is not None:
        interval_left = grid.vertical_axis_x + x_interval.left * grid.vertical.step
        interval_right = grid.vertical_axis_x + x_interval.right * grid.vertical.step
        left = max(left, int(math.floor(min(interval_left, interval_right))))
        right = min(right, int(math.ceil(max(interval_left, interval_right))))
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

    max_delta = min(32, max(5, int(math.ceil(step * 0.70))))
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
        threshold=max(12, int(round(step * 1.25))),
        minLineLength=max(18, int(round(step * 2.8))),
        maxLineGap=max(3, int(round(step * 0.45))),
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
        if int(selected.sum()) < max(20, int(round(step * 2.0))):
            break
        x_values = foreground_x[selected].astype(np.float64)
        y_values = foreground_y[selected].astype(np.float64)
        weights = darkness[foreground_y[selected], foreground_x[selected]].astype(np.float64)
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
        threshold=max(10, int(round(step * 0.90))),
        minLineLength=max(10, int(round(step * 1.25))),
        maxLineGap=max(3, int(round(step * 0.45))),
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
        weights = darkness[selected_y[near_seed], selected_x[near_seed]].astype(np.float64)
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
    tangent_distance = np.abs(
        tangent.slope * xx - yy + tangent.intercept
    ) / math.sqrt(tangent.slope * tangent.slope + 1.0)
    radius = max(3.0, step * 0.34)
    dark_threshold = max(0.50, grid.detection_threshold * 2.25)
    minimum_dark_pixels = max(5, int(round(step * 0.35)))
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
        if not (radius <= pixel_x < width - radius and radius <= pixel_y < height - radius):
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
    max_delta = min(32, max(5, int(math.ceil(step * 0.70))))
    scale = 14.0 / max(4.0, step)
    previous = np.full(height, -1e9, dtype=np.float32)
    previous[int(np.clip(anchor_y, 0, height - 1))] = 0.0
    back_steps: list[np.ndarray] = []
    last_supported_index = 0
    last_supported_y = int(np.clip(anchor_y, 0, height - 1))
    last_supported_score = 0.0
    unsupported_columns = 0
    maximum_gap = max(7, int(round(step * 0.70)))

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
        local_evidence = float(evidence[local_start:local_end, pixel_x].max(initial=-1.0))
        if local_evidence > 0.02:
            last_supported_index = path_index
            last_supported_y = pixel_y
            last_supported_score = float(current[pixel_y])
            unsupported_columns = 0
        else:
            unsupported_columns += 1
        previous = current
        if unsupported_columns >= maximum_gap and path_index >= int(round(step)):
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
    tangent_mask = (
        (tangent_distance <= max(2.5, step * 0.23))
        & (np.abs(xx - guide.pixel_x) > contact_window)
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

    anchor_x = int(round(guide.pixel_x))
    anchor_y = int(round(guide.end_y))
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


def _nearest(value: float, candidates: tuple[float, ...]) -> float:
    """Return the nearest value with deterministic tie-breaking."""
    return float(min(candidates, key=lambda candidate: (abs(candidate - value), candidate)))


def _logical_point(pixel_x: float, pixel_y: float, grid: GridModel) -> tuple[float, float]:
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
    window = min(len(jumps), max(8, int(round(grid.vertical.step * 1.5))))
    flat_tolerance = max(2.0, grid.horizontal.step * 0.22)
    start_cut = 0
    end_cut = len(points)
    start_trimmed = False
    end_trimmed = False

    for run_start, run_end in _large_jump_runs(jumps[:window], jump_threshold):
        run_length = run_end - run_start + 1
        prefix = points[: run_start + 1, 1]
        if run_length >= 2 and len(prefix) >= 3 and float(np.ptp(prefix)) <= flat_tolerance:
            start_cut = run_end + 1
            start_trimmed = True

    offset = len(jumps) - window
    for local_start, local_end in _large_jump_runs(jumps[-window:], jump_threshold):
        run_start = offset + local_start
        run_end = offset + local_end
        run_length = run_end - run_start + 1
        suffix = points[run_end + 1 :, 1]
        if run_length >= 2 and len(suffix) >= 3 and float(np.ptp(suffix)) <= flat_tolerance:
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

    raw_start_x, raw_start_y = map(float, points[0])
    raw_end_x, raw_end_y = map(float, points[-1])
    start_x_line = _nearest(raw_start_x, vertical_lines)
    end_x_line = _nearest(raw_end_x, vertical_lines)
    start_x = start_x_line if abs(start_x_line - raw_start_x) <= x_tolerance else raw_start_x
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
    simplified = cv2.approxPolyDP(smoothed.reshape(-1, 1, 2), epsilon, False).reshape(-1, 2)
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
        force_start_open=start_tail_trimmed or bool(x_interval and x_interval.left_open),
        force_end_open=end_tail_trimmed or bool(x_interval and x_interval.right_open),
    )
    smoothed, simplified = smooth_and_simplify_curve(
        points,
        grid,
        smoothing_cells=smoothing_cells,
        simplify_cells=simplify_cells,
    )
    return darkness, grid, TraceResult(raw_points, smoothed, simplified, score, start, end)


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
    return darkness, grid, TraceResult(
        raw_points,
        smoothed,
        simplified,
        score,
        start,
        end,
        tangent=tangent,
        vertical_guide=vertical_guide,
        tangent_markers=tangent_markers,
    )


def _fmt(value: float, digits: int = 2) -> str:
    """Format a stable compact SVG number."""
    rounded = round(float(value), digits)
    if abs(rounded - round(rounded)) < 10 ** (-digits):
        return str(int(round(rounded)))
    return f"{rounded:.{digits}f}".rstrip("0").rstrip(".")


def _coordinate_label(value: float) -> str:
    """Format a logical coordinate and use a mathematical minus sign."""
    nearest_integer = round(value)
    if abs(value - nearest_integer) <= 0.16:
        text = str(int(nearest_integer))
    else:
        text = _fmt(value, 1)
    return text.replace("-", "−")


def infer_graph_kind(condition_text: str | None, explicit_kind: str | None = None) -> str:
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
    mapped[:, 0] = ((points[:, 0] - first_x) / grid.vertical.step + pad_cells) * cell_size
    mapped[:, 1] = ((points[:, 1] - first_y) / grid.horizontal.step + pad_cells) * cell_size
    return mapped


def _polyline_path(points: np.ndarray) -> str:
    """Build a straight-segment SVG path through all knots."""
    commands = [f"M{_fmt(points[0, 0])} {_fmt(points[0, 1])}"]
    commands.extend(f"L{_fmt(x)} {_fmt(y)}" for x, y in points[1:])
    return " ".join(commands)


def _pchip_slopes(points: np.ndarray) -> np.ndarray:
    """Compute shape-preserving Hermite slopes for knots with increasing x coordinates."""
    x_values = points[:, 0].astype(np.float64)
    y_values = points[:, 1].astype(np.float64)
    intervals = np.diff(x_values)
    if np.any(intervals <= 0.0):
        raise ValueError("curve_knots_must_have_increasing_x")
    secants = np.diff(y_values) / intervals
    slopes = np.zeros(len(points), dtype=np.float64)
    if len(points) == 2:
        slopes[:] = secants[0]
        return slopes

    for index in range(1, len(points) - 1):
        left = secants[index - 1]
        right = secants[index]
        if left == 0.0 or right == 0.0 or left * right <= 0.0:
            slopes[index] = 0.0
            continue
        left_weight = 2.0 * intervals[index] + intervals[index - 1]
        right_weight = intervals[index] + 2.0 * intervals[index - 1]
        slopes[index] = (left_weight + right_weight) / (
            left_weight / left + right_weight / right
        )

    def endpoint_slope(here: float, neighbor: float, first: float, second: float) -> float:
        """Return a one-sided PCHIP slope clipped to the adjacent secants."""
        value = ((2.0 * here + neighbor) * first - here * second) / (here + neighbor)
        if value * first <= 0.0:
            return 0.0
        if first * second < 0.0 and abs(value) > 3.0 * abs(first):
            return 3.0 * first
        return value

    slopes[0] = endpoint_slope(intervals[0], intervals[1], secants[0], secants[1])
    slopes[-1] = endpoint_slope(
        intervals[-1],
        intervals[-2],
        secants[-1],
        secants[-2],
    )
    return slopes


def _cubic_path(points: np.ndarray) -> str:
    """Build a deterministic shape-preserving cubic SVG path through all knots."""
    if len(points) < 3:
        return _polyline_path(points)
    slopes = _pchip_slopes(points)
    commands = [f"M{_fmt(points[0, 0])} {_fmt(points[0, 1])}"]
    for index in range(len(points) - 1):
        current = points[index]
        following = points[index + 1]
        interval = float(following[0] - current[0])
        control_1 = np.asarray(
            [current[0] + interval / 3.0, current[1] + slopes[index] * interval / 3.0]
        )
        control_2 = np.asarray(
            [
                following[0] - interval / 3.0,
                following[1] - slopes[index + 1] * interval / 3.0,
            ]
        )
        commands.append(
            "C"
            f"{_fmt(control_1[0])} {_fmt(control_1[1])} "
            f"{_fmt(control_2[0])} {_fmt(control_2[1])} "
            f"{_fmt(following[0])} {_fmt(following[1])}"
        )
    return " ".join(commands)


def _unit_vector(vector: np.ndarray) -> np.ndarray:
    """Return a stable unit vector, or a zero vector for a degenerate input."""
    length = float(np.linalg.norm(vector))
    if length <= 1e-12:
        return np.zeros(2, dtype=np.float64)
    return vector.astype(np.float64) / length


def _bezier_point(segment: np.ndarray, parameter: float) -> np.ndarray:
    """Evaluate a cubic Bezier segment at one parameter value."""
    inverse = 1.0 - parameter
    return (
        inverse**3 * segment[0]
        + 3.0 * inverse * inverse * parameter * segment[1]
        + 3.0 * inverse * parameter * parameter * segment[2]
        + parameter**3 * segment[3]
    )


def _bezier_derivatives(
    segment: np.ndarray,
    parameter: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Evaluate the first and second derivatives of a cubic Bezier segment."""
    inverse = 1.0 - parameter
    first = 3.0 * (
        inverse * inverse * (segment[1] - segment[0])
        + 2.0 * inverse * parameter * (segment[2] - segment[1])
        + parameter * parameter * (segment[3] - segment[2])
    )
    second = 6.0 * (
        inverse * (segment[2] - 2.0 * segment[1] + segment[0])
        + parameter * (segment[3] - 2.0 * segment[2] + segment[1])
    )
    return first, second


def _chord_parameters(points: np.ndarray) -> np.ndarray:
    """Parameterize ordered points by normalized cumulative chord length."""
    distances = np.linalg.norm(np.diff(points, axis=0), axis=1)
    cumulative = np.concatenate([[0.0], np.cumsum(distances)])
    if cumulative[-1] <= 1e-12:
        return np.linspace(0.0, 1.0, len(points), dtype=np.float64)
    return cumulative / cumulative[-1]


def _generate_bezier_segment(
    points: np.ndarray,
    parameters: np.ndarray,
    left_tangent: np.ndarray,
    right_tangent: np.ndarray,
) -> np.ndarray:
    """Fit one cubic Bezier segment with fixed endpoint tangent directions."""
    first = points[0].astype(np.float64)
    last = points[-1].astype(np.float64)
    c00 = c01 = c11 = x0 = x1 = 0.0
    for point, parameter in zip(points, parameters):
        inverse = 1.0 - float(parameter)
        basis_0 = inverse**3
        basis_1 = 3.0 * float(parameter) * inverse * inverse
        basis_2 = 3.0 * float(parameter) * float(parameter) * inverse
        basis_3 = float(parameter) ** 3
        tangent_0 = left_tangent * basis_1
        tangent_1 = right_tangent * basis_2
        residual = point - (
            first * (basis_0 + basis_1) + last * (basis_2 + basis_3)
        )
        c00 += float(np.dot(tangent_0, tangent_0))
        c01 += float(np.dot(tangent_0, tangent_1))
        c11 += float(np.dot(tangent_1, tangent_1))
        x0 += float(np.dot(tangent_0, residual))
        x1 += float(np.dot(tangent_1, residual))

    determinant = c00 * c11 - c01 * c01
    if abs(determinant) > 1e-12:
        alpha_left = (x0 * c11 - x1 * c01) / determinant
        alpha_right = (c00 * x1 - c01 * x0) / determinant
    else:
        alpha_left = alpha_right = 0.0

    chord = float(np.linalg.norm(last - first))
    minimum_alpha = max(1e-6, chord * 1e-6)
    if alpha_left < minimum_alpha or alpha_right < minimum_alpha:
        alpha_left = alpha_right = chord / 3.0

    # The traced object is a function y(x), so every fitted segment must also
    # advance monotonically in x.  An unconstrained least-squares fit can make
    # either handle longer than the segment's horizontal span, which reverses
    # the Bezier in x and creates a visible loop even though the trace itself is
    # sound.  Keep both handle directions, but cap their horizontal reach to a
    # third of the segment.  The recursive fitter will introduce extra segments
    # whenever the shorter handles no longer meet the requested error bound.
    horizontal_span = float(last[0] - first[0])
    if horizontal_span > 1e-9:
        if left_tangent[0] > 1e-9:
            alpha_left = min(alpha_left, horizontal_span / (3.0 * left_tangent[0]))
        if right_tangent[0] < -1e-9:
            alpha_right = min(alpha_right, horizontal_span / (-3.0 * right_tangent[0]))

    return np.asarray(
        [
            first,
            first + left_tangent * alpha_left,
            last + right_tangent * alpha_right,
            last,
        ],
        dtype=np.float64,
    )


def _maximum_bezier_error(
    points: np.ndarray,
    segment: np.ndarray,
    parameters: np.ndarray,
) -> tuple[float, int]:
    """Return maximum squared fitting error and its interior split index."""
    split = max(1, len(points) // 2)
    maximum = 0.0
    for index in range(1, len(points) - 1):
        difference = _bezier_point(segment, float(parameters[index])) - points[index]
        squared_error = float(np.dot(difference, difference))
        if squared_error > maximum:
            maximum = squared_error
            split = index
    return maximum, split


def _reparameterize_bezier(
    points: np.ndarray,
    segment: np.ndarray,
    parameters: np.ndarray,
) -> np.ndarray:
    """Improve fit parameters with one Newton-Raphson projection step."""
    improved = parameters.astype(np.float64).copy()
    for index, (point, parameter) in enumerate(zip(points, parameters)):
        curve_point = _bezier_point(segment, float(parameter))
        first, second = _bezier_derivatives(segment, float(parameter))
        difference = curve_point - point
        denominator = float(np.dot(first, first) + np.dot(difference, second))
        if abs(denominator) <= 1e-12:
            continue
        numerator = float(np.dot(difference, first))
        improved[index] = float(np.clip(parameter - numerator / denominator, 0.0, 1.0))
    improved[0] = 0.0
    improved[-1] = 1.0
    return improved


def _fit_bezier_recursive(
    points: np.ndarray,
    left_tangent: np.ndarray,
    right_tangent: np.ndarray,
    maximum_squared_error: float,
    *,
    depth: int = 0,
) -> list[np.ndarray]:
    """Adaptively fit C1-continuous cubic Bezier segments to ordered points."""
    if len(points) == 2:
        distance = float(np.linalg.norm(points[1] - points[0])) / 3.0
        return [
            np.asarray(
                [
                    points[0],
                    points[0] + left_tangent * distance,
                    points[1] + right_tangent * distance,
                    points[1],
                ],
                dtype=np.float64,
            )
        ]

    parameters = _chord_parameters(points)
    segment = _generate_bezier_segment(points, parameters, left_tangent, right_tangent)
    maximum_error, split = _maximum_bezier_error(points, segment, parameters)
    if maximum_error <= maximum_squared_error:
        return [segment]

    if maximum_error <= maximum_squared_error * 4.0:
        for _ in range(5):
            improved = _reparameterize_bezier(points, segment, parameters)
            if np.any(np.diff(improved) <= 0.0):
                break
            parameters = improved
            segment = _generate_bezier_segment(
                points,
                parameters,
                left_tangent,
                right_tangent,
            )
            maximum_error, split = _maximum_bezier_error(points, segment, parameters)
            if maximum_error <= maximum_squared_error:
                return [segment]

    if depth >= 64 or split <= 0 or split >= len(points) - 1:
        split = len(points) // 2
    center_tangent = _unit_vector(points[split - 1] - points[split + 1])
    if not np.any(center_tangent):
        center_tangent = _unit_vector(points[split - 1] - points[split])
    left_segments = _fit_bezier_recursive(
        points[: split + 1],
        left_tangent,
        center_tangent,
        maximum_squared_error,
        depth=depth + 1,
    )
    right_segments = _fit_bezier_recursive(
        points[split:],
        -center_tangent,
        right_tangent,
        maximum_squared_error,
        depth=depth + 1,
    )
    return left_segments + right_segments


def _bezier_path(points: np.ndarray, maximum_error: float) -> tuple[str, int]:
    """Fit and serialize an adaptive sequence of smooth cubic Bezier segments."""
    if len(points) < 3:
        return _polyline_path(points), max(1, len(points) - 1)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9])
    fitting_points = points[keep].astype(np.float64)
    left_tangent = _unit_vector(fitting_points[1] - fitting_points[0])
    right_tangent = _unit_vector(fitting_points[-2] - fitting_points[-1])
    segments = _fit_bezier_recursive(
        fitting_points,
        left_tangent,
        right_tangent,
        max(0.05, float(maximum_error)) ** 2,
    )
    commands = [f"M{_fmt(segments[0][0, 0])} {_fmt(segments[0][0, 1])}"]
    for segment in segments:
        commands.append(
            "C"
            f"{_fmt(segment[1, 0])} {_fmt(segment[1, 1])} "
            f"{_fmt(segment[2, 0])} {_fmt(segment[2, 1])} "
            f"{_fmt(segment[3, 0])} {_fmt(segment[3, 1])}"
        )
    return " ".join(commands), len(segments)


def _bezier_path_with_fixed_tangent(
    points: np.ndarray,
    anchor: np.ndarray,
    forward_tangent: np.ndarray,
    maximum_error: float,
) -> tuple[str, int]:
    """Fit both curve branches with an exact shared tangent at ``anchor``."""
    fitting_points = points[
        np.concatenate([[True], np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-9])
    ].astype(np.float64)
    anchor = anchor.astype(np.float64)
    direction = _unit_vector(forward_tangent)
    if len(fitting_points) < 3 or not np.any(direction):
        return _bezier_path(fitting_points, maximum_error)

    left = fitting_points[fitting_points[:, 0] < anchor[0] - 1e-7]
    right = fitting_points[fitting_points[:, 0] > anchor[0] + 1e-7]
    if len(left) < 1 or len(right) < 1:
        return _bezier_path(fitting_points, maximum_error)
    left = np.vstack([left, anchor])
    right = np.vstack([anchor, right])
    threshold = max(0.05, float(maximum_error)) ** 2
    left_segments = _fit_bezier_recursive(
        left,
        _unit_vector(left[1] - left[0]),
        -direction,
        threshold,
    )
    right_segments = _fit_bezier_recursive(
        right,
        direction,
        _unit_vector(right[-2] - right[-1]),
        threshold,
    )
    segments = left_segments + right_segments
    commands = [f"M{_fmt(segments[0][0, 0])} {_fmt(segments[0][0, 1])}"]
    for segment in segments:
        commands.append(
            "C"
            f"{_fmt(segment[1, 0])} {_fmt(segment[1, 1])} "
            f"{_fmt(segment[2, 0])} {_fmt(segment[2, 1])} "
            f"{_fmt(segment[3, 0])} {_fmt(segment[3, 1])}"
        )
    return " ".join(commands), len(segments)


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
    interval_count = max(2, int(math.ceil((x_values[-1] - x_values[0]) / interval)))
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

    vertical_grid_x = [index * cell_size for index in range(columns + 1)]
    horizontal_grid_y = [index * cell_size for index in range(rows + 1)]
    grid_path = " ".join(
        [f"M{_fmt(x)} 0V{_fmt(height)}" for x in vertical_grid_x]
        + [f"M0 {_fmt(y)}H{_fmt(width)}" for y in horizontal_grid_y]
    )

    first_x = grid.vertical_lines()[0]
    first_y = grid.horizontal_lines()[0]
    axis_x = ((grid.vertical_axis_x - first_x) / grid.vertical.step + pad_cells) * cell_size
    axis_y = ((grid.horizontal_axis_y - first_y) / grid.horizontal.step + pad_cells) * cell_size
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

    labels = ""
    ticks = ""
    escaped_graph_label = html.escape(graph_label)
    if include_labels:
        unit_y = axis_y - cell_size
        tick_half = max(2.5, cell_size * 0.15)
        ticks = (
            f'<path d="M{_fmt(start_svg[0])} {_fmt(axis_y - tick_half)}V{_fmt(axis_y + tick_half)} '
            f'M{_fmt(end_svg[0])} {_fmt(axis_y - tick_half)}V{_fmt(axis_y + tick_half)} '
            f'M{_fmt(axis_x - tick_half)} {_fmt(unit_y)}H{_fmt(axis_x + tick_half)}"/>'
        )
        labels = (
            '<g fill="#111" font-family="Times New Roman, Times, serif" font-size="12.5">'
            f'<text x="{_fmt(start_svg[0] - 7)}" y="{_fmt(axis_y + 16)}">'
            f'{_coordinate_label(trace.start.logical_x)}</text>'
            f'<text x="{_fmt(end_svg[0] - 4)}" y="{_fmt(axis_y + 16)}">'
            f'{_coordinate_label(trace.end.logical_x)}</text>'
            f'<text x="{_fmt(axis_x + 5)}" y="{_fmt(unit_y + 4)}">1</text>'
            f'<text x="{_fmt(axis_x + 5)}" y="{_fmt(axis_y + 16)}">0</text>'
            f'<text x="{_fmt(width - 11)}" y="{_fmt(axis_y + 17)}" font-size="15" '
            'font-style="italic">x</text>'
            f'<text x="{_fmt(axis_x - 13)}" y="15" font-size="15" font-style="italic">y</text>'
            f'<text x="{_fmt(max(4, width - 88))}" y="15" font-size="13" '
            f'font-style="italic">{escaped_graph_label}</text>'
            '</g>'
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
        (grid.vertical_lines()[0] - grid.vertical_axis_x) / grid.vertical.step
        - pad_cells
    )
    x_max = x_min + columns
    y_max = (
        (grid.horizontal_axis_y - grid.horizontal_lines()[0]) / grid.horizontal.step
        + pad_cells
    )
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
    right = [point for point in candidates if point[0] >= logical_x_0 + minimum_distance]
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
    tangent = trace.tangent
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
    axis_x = ((grid.vertical_axis_x - first_x) / grid.vertical.step + pad_cells) * cell_size
    axis_y = ((grid.horizontal_axis_y - first_y) / grid.horizontal.step + pad_cells) * cell_size
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
    lattice_svg = _logical_points_to_svg(
        lattice_logical,
        logical_bounds,
        cell_size,
    ) if len(lattice_logical) else np.empty((0, 2), dtype=np.float64)
    tangency_svg = guide_svg[1]
    x_axis_guide_svg = guide_svg[0]
    end_svg = _map_points_to_svg(
        np.asarray([[trace.end.pixel_x, trace.end.pixel_y]], dtype=np.float32),
        grid,
        cell_size=cell_size,
        pad_cells=pad_cells,
    )[0]

    escaped_graph_label = html.escape(graph_label)
    escaped_guide_label = html.escape(guide.label)
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
            '</g>'
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


def _rounded_points(points: np.ndarray, digits: int = 4) -> list[list[float]]:
    """Convert a NumPy point array to stable JSON-ready rounded values."""
    return [[round(float(x), digits), round(float(y), digits)] for x, y in points]


def diagnostics_payload(
    source: str,
    rgba: np.ndarray,
    grid: GridModel,
    trace: TraceResult,
    *,
    foreground_threshold: float,
) -> dict:
    """Build the reproducibility report saved beside the generated SVG."""
    logical_knots = np.asarray(
        [_logical_point(float(x), float(y), grid) for x, y in trace.simplified_points],
        dtype=np.float64,
    )
    payload = {
        "source": source,
        "image": {"width": int(rgba.shape[1]), "height": int(rgba.shape[0])},
        "foreground_threshold": float(foreground_threshold),
        "grid": {
            "vertical_lines": [round(value, 6) for value in grid.vertical_lines()],
            "horizontal_lines": [round(value, 6) for value in grid.horizontal_lines()],
            "vertical_step": round(grid.vertical.step, 6),
            "horizontal_step": round(grid.horizontal.step, 6),
            "vertical_max_residual": round(grid.vertical.max_residual, 6),
            "horizontal_max_residual": round(grid.horizontal.max_residual, 6),
            "vertical_axis_x": round(grid.vertical_axis_x, 6),
            "horizontal_axis_y": round(grid.horizontal_axis_y, 6),
            "grid_mask_radius": int(grid.grid_mask_radius),
            "detection_threshold": round(grid.detection_threshold, 6),
        },
        "curve": {
            "trace_score": round(trace.score, 6),
            "raw_span_pixels": round(float(trace.raw_points[-1, 0] - trace.raw_points[0, 0]), 6),
            "raw_point_count": int(len(trace.raw_points)),
            "simplified_point_count": int(len(trace.simplified_points)),
            "pixel_knots": _rounded_points(trace.simplified_points),
            "logical_knots": _rounded_points(logical_knots),
            "start": {
                "pixel": [round(trace.start.pixel_x, 4), round(trace.start.pixel_y, 4)],
                "logical": [round(trace.start.logical_x, 4), round(trace.start.logical_y, 4)],
                "looks_open": bool(trace.start.looks_open),
            },
            "end": {
                "pixel": [round(trace.end.pixel_x, 4), round(trace.end.pixel_y, 4)],
                "logical": [round(trace.end.logical_x, 4), round(trace.end.logical_y, 4)],
                "looks_open": bool(trace.end.looks_open),
            },
        },
    }
    if trace.tangent is not None:
        payload["tangent"] = {
            "pixel_line": {
                "slope": round(trace.tangent.slope, 8),
                "intercept": round(trace.tangent.intercept, 8),
                "start_x": round(trace.tangent.start_x, 4),
                "end_x": round(trace.tangent.end_x, 4),
            },
            "logical_slope": round(trace.tangent.logical_slope, 8),
            "logical_intercept": round(trace.tangent.logical_intercept, 8),
            "support_pixels": int(trace.tangent.support_pixels),
        }
        if trace.tangent_markers is not None:
            payload["tangent"]["marked_lattice_points"] = _rounded_points(
                trace.tangent_markers
            )
    if trace.vertical_guide is not None:
        payload["vertical_guide"] = {
            "pixel_x": round(trace.vertical_guide.pixel_x, 4),
            "start_y": round(trace.vertical_guide.start_y, 4),
            "end_y": round(trace.vertical_guide.end_y, 4),
            "label": trace.vertical_guide.label,
        }
    return payload


def save_debug_overlay(
    rgba: np.ndarray,
    grid: GridModel,
    trace: TraceResult,
    output: Path,
) -> None:
    """Save a visual audit overlay without affecting extraction decisions."""
    source = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
    canvas = Image.new("RGBA", source.size, (255, 255, 255, 255))
    canvas.alpha_composite(source)
    draw = ImageDraw.Draw(canvas)
    width, height = canvas.size
    for x in grid.vertical_lines():
        draw.line((x, 0, x, height - 1), fill=(0, 170, 190, 150), width=1)
    for y in grid.horizontal_lines():
        draw.line((0, y, width - 1, y), fill=(0, 170, 190, 150), width=1)
    draw.line(
        (grid.vertical_axis_x, 0, grid.vertical_axis_x, height - 1),
        fill=(225, 50, 50, 220),
        width=2,
    )
    draw.line(
        (0, grid.horizontal_axis_y, width - 1, grid.horizontal_axis_y),
        fill=(225, 50, 50, 220),
        width=2,
    )
    if trace.tangent is not None:
        draw.line(
            (
                trace.tangent.start_x,
                trace.tangent.y_at(trace.tangent.start_x),
                trace.tangent.end_x,
                trace.tangent.y_at(trace.tangent.end_x),
            ),
            fill=(235, 120, 20, 255),
            width=2,
        )
    if trace.vertical_guide is not None:
        draw.line(
            (
                trace.vertical_guide.pixel_x,
                trace.vertical_guide.start_y,
                trace.vertical_guide.pixel_x,
                trace.vertical_guide.end_y,
            ),
            fill=(150, 40, 180, 255),
            width=2,
        )
    draw.line([tuple(map(float, point)) for point in trace.points], fill=(20, 80, 220, 255), width=2)
    radius = 3
    for endpoint in (trace.start, trace.end):
        draw.ellipse(
            (
                endpoint.pixel_x - radius,
                endpoint.pixel_y - radius,
                endpoint.pixel_x + radius,
                endpoint.pixel_y + radius,
            ),
            outline=(0, 150, 40, 255),
            width=2,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output)


def run(
    source: str,
    out_dir: Path,
    *,
    cell_size: float,
    pad_cells: int,
    foreground_threshold: float,
    grid_mask_radius: int | None,
    vertical_axis_x: float | None,
    horizontal_axis_y: float | None,
    minimum_span_cells: float,
    snap_tolerance_cells: float,
    smoothing_cells: float,
    simplify_cells: float,
    path_mode: str,
    bezier_error_cells: float,
    endpoint_style: str,
    include_labels: bool,
    curve_color: str,
    condition_text: str | None,
    graph_label: str | None,
    diagram_kind: str | None,
    x_min: float | None,
    x_max: float | None,
    debug_overlay: bool,
) -> tuple[Path, Path, Path | None]:
    """Extract one raster graph and write its SVG and deterministic diagnostics."""
    rgba, _ = load_image(source)
    resolved_x_interval = infer_x_interval(condition_text)
    if (x_min is None) != (x_max is None):
        raise ValueError("--x-min and --x-max must be provided together")
    if x_min is not None and x_max is not None:
        if x_max <= x_min:
            raise ValueError("--x-max must be greater than --x-min")
        resolved_x_interval = XInterval(x_min, x_max, True, True)
    resolved_diagram_kind = infer_graph_kind(condition_text, diagram_kind)
    if resolved_diagram_kind == "function_with_tangent":
        _, grid, trace = extract_graph_with_tangent(
            rgba,
            foreground_threshold=foreground_threshold,
            grid_mask_radius=grid_mask_radius,
            vertical_axis_x=vertical_axis_x,
            horizontal_axis_y=horizontal_axis_y,
            snap_tolerance_cells=snap_tolerance_cells,
            # Black tangent diagrams need a slightly wider centerline filter
            # than chromatic single-curve diagrams: after the straight line is
            # removed, the remaining raster stroke still alternates between
            # its upper and lower antialiased edges from one column to the next.
            smoothing_cells=max(smoothing_cells, 0.075),
            simplify_cells=max(simplify_cells, 0.050),
        )
    else:
        _, grid, trace = extract_graph(
            rgba,
            foreground_threshold=foreground_threshold,
            grid_mask_radius=grid_mask_radius,
            vertical_axis_x=vertical_axis_x,
            horizontal_axis_y=horizontal_axis_y,
            minimum_span_cells=minimum_span_cells,
            snap_tolerance_cells=snap_tolerance_cells,
            smoothing_cells=smoothing_cells,
            simplify_cells=simplify_cells,
            x_interval=resolved_x_interval,
        )
    resolved_graph_label = infer_graph_label(condition_text, graph_label)
    renderer = (
        render_graph_with_tangent_svg
        if resolved_diagram_kind == "function_with_tangent"
        else render_svg
    )
    render_pad_cells = 0 if resolved_diagram_kind == "function_with_tangent" else pad_cells
    svg = renderer(
        grid,
        trace,
        cell_size=cell_size,
        pad_cells=render_pad_cells,
        path_mode=path_mode,
        bezier_error_cells=bezier_error_cells,
        endpoint_style=endpoint_style,
        include_labels=include_labels,
        curve_color=curve_color,
        graph_label=resolved_graph_label,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    asset_id = extract_id(source)
    svg_path = out_dir / f"{asset_id}.svg"
    json_path = out_dir / f"{asset_id}.json"
    overlay_path = out_dir / f"{asset_id}.debug.png" if debug_overlay else None
    svg_path.write_text(svg, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            diagnostics_payload(
                source,
                rgba,
                grid,
                trace,
                foreground_threshold=foreground_threshold,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if overlay_path is not None:
        save_debug_overlay(rgba, grid, trace, overlay_path)

    print(f"svg={svg_path}")
    print(f"diagnostics={json_path}")
    if overlay_path is not None:
        print(f"debug_overlay={overlay_path}")
    print(f"grid_step=({_fmt(grid.vertical.step, 4)}, {_fmt(grid.horizontal.step, 4)})")
    print(
        "axes="
        f"(vertical_x={_fmt(grid.vertical_axis_x, 3)}, "
        f"horizontal_y={_fmt(grid.horizontal_axis_y, 3)})"
    )
    print(
        "curve_endpoints="
        f"[({_fmt(trace.start.logical_x, 3)}, {_fmt(trace.start.logical_y, 3)}), "
        f"({_fmt(trace.end.logical_x, 3)}, {_fmt(trace.end.logical_y, 3)})]"
    )
    print(f"graph_label={resolved_graph_label}")
    print(f"diagram_kind={resolved_diagram_kind}")
    if trace.tangent is not None:
        print(f"tangent_slope={_fmt(trace.tangent.logical_slope, 6)}")
    if resolved_x_interval is not None and resolved_diagram_kind == "single_curve":
        print(
            "condition_x_interval="
            f"({_fmt(resolved_x_interval.left, 3)}, {_fmt(resolved_x_interval.right, 3)})"
        )
    return svg_path, json_path, overlay_path


def main() -> None:
    """Parse CLI options and run the deterministic graph vectorizer."""
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically detect a Cartesian grid, suppress it, trace the dominant "
            "function curve by contrast, and render a normalized SVG."
        )
    )
    parser.add_argument("source", help="Path or URL to a PNG/JPEG/BMP raster graph")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("graph_svg_from_contrast"),
        help="Output directory for SVG, JSON, and optional debug overlay",
    )
    parser.add_argument("--cell-size", type=float, default=20.0, help="SVG grid cell size")
    parser.add_argument("--pad-cells", type=int, default=1, help="Extra grid cells around the source grid")
    parser.add_argument(
        "--foreground-threshold",
        type=float,
        default=0.20,
        help="Visible-darkness threshold used only for long grid-line detection",
    )
    parser.add_argument(
        "--grid-mask-radius",
        type=int,
        default=None,
        help="Pixels removed around every detected grid line; default is scale-dependent",
    )
    parser.add_argument(
        "--vertical-axis-x",
        type=float,
        default=None,
        help="Override the automatically detected y-axis x position in source pixels",
    )
    parser.add_argument(
        "--horizontal-axis-y",
        type=float,
        default=None,
        help="Override the automatically detected x-axis y position in source pixels",
    )
    parser.add_argument(
        "--minimum-span-cells",
        type=float,
        default=3.0,
        help="Reject traces shorter than this many grid cells",
    )
    parser.add_argument(
        "--snap-tolerance-cells",
        type=float,
        default=0.22,
        help="Endpoint-to-grid snapping tolerance measured in cells",
    )
    parser.add_argument(
        "--smoothing-cells",
        type=float,
        default=0.030,
        help="Gaussian trace smoothing sigma measured in cells",
    )
    parser.add_argument(
        "--simplify-cells",
        type=float,
        default=0.035,
        help="Curve-knot simplification tolerance measured in cells",
    )
    parser.add_argument(
        "--path-mode",
        choices=("bezier", "cubic", "polyline"),
        default="bezier",
        help="Render adaptive Bezier fitting, shape-preserving cubic knots, or a polyline",
    )
    parser.add_argument(
        "--bezier-error-cells",
        type=float,
        default=0.030,
        help="Maximum adaptive Bezier fitting error measured in grid cells",
    )
    parser.add_argument(
        "--endpoint-style",
        choices=("auto", "open", "closed", "none"),
        default="auto",
        help="Endpoint rendering; auto draws circles only when ring overhang is detected",
    )
    parser.add_argument("--no-labels", action="store_true", help="Omit coordinate labels and ticks")
    parser.add_argument("--curve-color", default="#143b8f", help="SVG curve stroke color")
    parser.add_argument(
        "--condition-text",
        default=None,
        help="Condition text used to infer y=f(x), y=f′(x), y=f″(x), or y=F(x)",
    )
    parser.add_argument(
        "--graph-label",
        default=None,
        help="Explicit SVG graph label; overrides --condition-text inference",
    )
    parser.add_argument(
        "--diagram-kind",
        choices=("auto", "single_curve", "function_with_tangent"),
        default="auto",
        help="Extractor selection; auto routes from the condition text",
    )
    parser.add_argument("--x-min", type=float, default=None, help="Explicit logical left x bound")
    parser.add_argument("--x-max", type=float, default=None, help="Explicit logical right x bound")
    parser.add_argument(
        "--debug-overlay",
        action="store_true",
        help="Also save a raster overlay of detected grid, axes, trace, and endpoints",
    )
    args = parser.parse_args()

    run(
        args.source,
        args.out_dir,
        cell_size=args.cell_size,
        pad_cells=args.pad_cells,
        foreground_threshold=args.foreground_threshold,
        grid_mask_radius=args.grid_mask_radius,
        vertical_axis_x=args.vertical_axis_x,
        horizontal_axis_y=args.horizontal_axis_y,
        minimum_span_cells=args.minimum_span_cells,
        snap_tolerance_cells=args.snap_tolerance_cells,
        smoothing_cells=args.smoothing_cells,
        simplify_cells=args.simplify_cells,
        path_mode=args.path_mode,
        bezier_error_cells=args.bezier_error_cells,
        endpoint_style=args.endpoint_style,
        include_labels=not args.no_labels,
        curve_color=args.curve_color,
        condition_text=args.condition_text,
        graph_label=args.graph_label,
        diagram_kind=args.diagram_kind,
        x_min=args.x_min,
        x_max=args.x_max,
        debug_overlay=args.debug_overlay,
    )


if __name__ == "__main__":
    main()
