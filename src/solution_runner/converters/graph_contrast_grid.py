"""Detect a Cartesian lattice in a raster graph."""

from __future__ import annotations

import itertools
import math
from collections import Counter

import cv2
import numpy as np

from .graph_contrast_models import GridAxisModel, GridModel


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
        centers.append(
            float(np.average(np.asarray(group, dtype=np.float64), weights=weights))
        )
    return centers


def _step_candidates(values: np.ndarray, axis_size: int) -> list[float]:
    """Generate stable grid-step candidates from all pairwise line distances."""
    min_step = max(4.0, float(axis_size) * 0.012)
    max_step = max(min_step, float(axis_size) * 0.35)
    candidates: list[float] = []
    for left, right in itertools.combinations(values, 2):
        distance = float(right - left)
        if distance < min_step:
            continue
        max_divisor = min(16, max(1, math.floor(distance / min_step)))
        for divisor in range(1, max_divisor + 1):
            candidate = distance / divisor
            if min_step <= candidate <= max_step:
                candidates.append(candidate)
    if not candidates:
        return []

    bin_width = max(0.25, float(axis_size) * 0.001)
    bins = Counter(round(candidate / bin_width) for candidate in candidates)
    return [key * bin_width for key, _ in bins.most_common(80)]


def fit_grid_axis(
    centers: list[float],
    axis_size: int,
    preferred_step: float | None = None,
) -> GridAxisModel:
    """Fit a regular one-dimensional lattice while rejecting missing-line subharmonics."""
    if len(centers) < 4:
        raise ValueError(
            f"not_enough_grid_lines: found {len(centers)}, need at least 4"
        )

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
    matched_values = np.asarray(
        [matched[int(index)][0] for index in lattice], dtype=np.float64
    )
    design = np.column_stack([np.ones_like(lattice), lattice])
    origin, step = np.linalg.lstsq(design, matched_values, rcond=None)[0]
    if step <= 0.0:
        raise ValueError("invalid_grid_step")

    first_index = round((float(values.min()) - origin) / step)
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
    index = round(coordinate)
    if vertical:
        if not 0 <= index < darkness.shape[1]:
            return -math.inf
        profile = darkness[
            :, max(0, index - 1) : min(darkness.shape[1], index + 2)
        ].max(axis=1)
    else:
        if not 0 <= index < darkness.shape[0]:
            return -math.inf
        profile = darkness[
            max(0, index - 1) : min(darkness.shape[0], index + 2), :
        ].max(axis=0)

    lower = max(0, math.floor(plot_min))
    upper = min(len(profile), math.ceil(plot_max) + 1)
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


def _fit_square_grid(darkness, foreground_threshold):
    """Fit both grid axes across descending contrast thresholds."""
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
        multiple = round(ratio)
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
            last_error = ValueError(
                f"grid_step_ratio_not_square_enough: {final_ratio:.3f}"
            )
            continue
        vertical = candidate_vertical
        horizontal = candidate_horizontal
        detection_threshold = threshold
        break

    if vertical is None or horizontal is None:
        raise last_error or ValueError("grid_not_found_at_any_contrast_threshold")

    return vertical, horizontal, detection_threshold


def detect_grid(
    darkness: np.ndarray,
    *,
    foreground_threshold: float,
    grid_mask_radius: int | None,
    vertical_axis_x: float | None,
    horizontal_axis_y: float | None,
) -> GridModel:
    """Detect the regular Cartesian grid and its horizontal and vertical axes."""
    vertical, horizontal, detection_threshold = _fit_square_grid(
        darkness, foreground_threshold
    )

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
        max(0, round(min(vertical.step, horizontal.step) * 0.025))
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
            detected_horizontal_axis_y
            if horizontal_axis_y is None
            else horizontal_axis_y
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
