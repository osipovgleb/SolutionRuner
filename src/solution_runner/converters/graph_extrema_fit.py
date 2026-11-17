"""Fit a shape-preserving curve through extrema and landmarks."""

from __future__ import annotations

import itertools
import math

import numpy as np
from scipy.interpolate import CubicSpline

from . import graph_png_to_svg_by_contrast as base
from .graph_extrema_types import ExtremaFit, Extremum, Landmark


def _pchip_slopes_with_extrema(
    points: np.ndarray,
    extrema_indices: tuple[int, ...],
    *,
    smoothing: float = 0.14,
    extremum_rounding: float = 0.12,
) -> np.ndarray:
    """Compute shape-preserving slopes with gently rounded extrema."""
    slopes = base._pchip_slopes(points)
    amount = float(np.clip(smoothing, 0.0, 1.0))
    if amount > 0.0 and len(points) >= 4:
        natural_slopes = CubicSpline(
            points[:, 0],
            points[:, 1],
            bc_type="natural",
        )(points[:, 0], 1)
        slopes[1:-1] = (1.0 - amount) * slopes[1:-1] + amount * natural_slopes[1:-1]

    extrema_set = set(extrema_indices)
    rounding = float(np.clip(extremum_rounding, 0.0, 1.0))
    if rounding > 0.0:
        # A parabola through an extremum and one neighboring knot would have a
        # neighbor derivative equal to twice that segment's secant. Blend only
        # a small amount toward that value. Each side contributes independently,
        # so asymmetric raster geometry stays asymmetric; a knot shared by two
        # close extrema receives the mean of their two local suggestions.
        neighbor_targets: dict[int, list[float]] = {}
        for extremum_index in extrema_indices:
            for neighbor_index in (extremum_index - 1, extremum_index + 1):
                if (
                    neighbor_index <= 0
                    or neighbor_index >= len(points) - 1
                    or neighbor_index in extrema_set
                ):
                    continue
                left_index = min(extremum_index, neighbor_index)
                right_index = max(extremum_index, neighbor_index)
                width = float(points[right_index, 0] - points[left_index, 0])
                if width <= 1e-12:
                    continue
                secant = float((points[right_index, 1] - points[left_index, 1]) / width)
                neighbor_targets.setdefault(neighbor_index, []).append(2.0 * secant)
        for neighbor_index, targets in neighbor_targets.items():
            target = float(np.mean(targets))
            slopes[neighbor_index] = (1.0 - rounding) * slopes[
                neighbor_index
            ] + rounding * target

    if len(points) >= 3:
        # Neither global smoothing nor the small extremum bias may create a new
        # turning point. Clip every derivative to its adjacent monotone secants,
        # then apply the standard cubic-Hermite segment limiter.
        secants = np.diff(points[:, 1]) / np.diff(points[:, 0])
        for index in range(1, len(points) - 1):
            if index in extrema_set:
                slopes[index] = 0.0
                continue
            left = float(secants[index - 1])
            right = float(secants[index])
            if left == 0.0 or right == 0.0 or left * right <= 0.0:
                slopes[index] = 0.0
                continue
            sign = 1.0 if left > 0.0 else -1.0
            magnitude = min(
                abs(float(slopes[index])),
                3.0 * min(abs(left), abs(right)),
            )
            slopes[index] = sign * magnitude

        for index, secant in enumerate(secants):
            if abs(float(secant)) <= 1e-12:
                slopes[index] = 0.0
                slopes[index + 1] = 0.0
                continue
            alpha = float(slopes[index] / secant)
            beta = float(slopes[index + 1] / secant)
            if alpha < 0.0:
                slopes[index] = 0.0
                alpha = 0.0
            if beta < 0.0:
                slopes[index + 1] = 0.0
                beta = 0.0
            norm = math.hypot(alpha, beta)
            if norm > 3.0:
                scale = 3.0 / norm
                slopes[index] = scale * alpha * secant
                slopes[index + 1] = scale * beta * secant
    if extrema_indices:
        slopes[np.asarray(extrema_indices, dtype=np.int64)] = 0.0
    return slopes


def _evaluate_hermite(
    knots: np.ndarray,
    slopes: np.ndarray,
    x_values: np.ndarray,
) -> np.ndarray:
    """Evaluate a piecewise cubic Hermite curve at ordered logical x values."""
    interval_indices = np.searchsorted(knots[:, 0], x_values, side="right") - 1
    interval_indices = np.clip(interval_indices, 0, len(knots) - 2)
    left = knots[interval_indices]
    right = knots[interval_indices + 1]
    width = right[:, 0] - left[:, 0]
    parameter = np.clip((x_values - left[:, 0]) / width, 0.0, 1.0)
    parameter_2 = parameter * parameter
    parameter_3 = parameter_2 * parameter
    h00 = 2.0 * parameter_3 - 3.0 * parameter_2 + 1.0
    h10 = parameter_3 - 2.0 * parameter_2 + parameter
    h01 = -2.0 * parameter_3 + 3.0 * parameter_2
    h11 = parameter_3 - parameter_2
    return (
        h00 * left[:, 1]
        + h10 * width * slopes[interval_indices]
        + h01 * right[:, 1]
        + h11 * width * slopes[interval_indices + 1]
    )


def _project_between_extrema(
    analysis_trace: np.ndarray,
    hard_points: np.ndarray,
) -> np.ndarray:
    """Remove raster-scale reversals while preserving each monotone extremum branch."""
    projected = analysis_trace.astype(np.float64).copy()
    for left, right in itertools.pairwise(hard_points):
        mask = (projected[:, 0] > left[0]) & (projected[:, 0] < right[0])
        if not np.any(mask):
            continue
        values = projected[mask, 1]
        lower = min(float(left[1]), float(right[1]))
        upper = max(float(left[1]), float(right[1]))
        values = np.clip(values, lower, upper)
        if right[1] > left[1] + 1e-9:
            values = np.maximum.accumulate(np.concatenate([[left[1]], values]))[1:]
            values = np.minimum(values, right[1])
        elif right[1] < left[1] - 1e-9:
            values = np.minimum.accumulate(np.concatenate([[left[1]], values]))[1:]
            values = np.maximum(values, right[1])
        else:
            values.fill(float(left[1]))

        # A microscopic blend with the branch chord breaks pixel-induced equal
        # runs.  It is far below SVG rounding but prevents extra zero-slope
        # support knots and therefore visible horizontal shelves at extrema.
        x_fraction = (projected[mask, 0] - left[0]) / (right[0] - left[0])
        chord = left[1] + x_fraction * (right[1] - left[1])
        projected[mask, 1] = values * (1.0 - 1e-4) + chord * 1e-4
    return projected


def fit_logical_curve(
    analysis_trace: np.ndarray,
    extrema: tuple[Extremum, ...],
    landmarks: tuple[Landmark, ...] = (),
    *,
    maximum_error_cells: float = 0.08,
    minimum_support_spacing_cells: float = 0.18,
    extremum_shoulder_cells: float = 0.50,
    slope_smoothing: float = 0.14,
    extremum_rounding: float = 0.12,
    maximum_knots: int = 160,
) -> ExtremaFit:
    """Fit an adaptive shape-preserving Hermite curve through hard extrema knots."""
    if len(analysis_trace) < 2:
        raise ValueError("at_least_two_trace_points_are_required")
    start = analysis_trace[0].astype(np.float64)
    end = analysis_trace[-1].astype(np.float64)
    interior_extrema = tuple(
        extremum
        for extremum in extrema
        if start[0] + minimum_support_spacing_cells
        < extremum.x
        < end[0] - minimum_support_spacing_cells
    )
    hard_points = np.asarray(
        [start, *([np.asarray([item.x, item.y]) for item in interior_extrema]), end],
        dtype=np.float64,
    )
    hard_points = hard_points[np.argsort(hard_points[:, 0])]
    if np.any(np.diff(hard_points[:, 0]) <= 1e-7):
        raise ValueError("extrema_collapsed_to_duplicate_x_coordinates")

    target_trace = _project_between_extrema(analysis_trace, hard_points)
    knot_rows: list[tuple[float, float, bool]] = [
        (float(point[0]), float(point[1]), 0 < index < len(hard_points) - 1)
        for index, point in enumerate(hard_points)
    ]
    used_landmarks: list[Landmark] = []
    landmark_spacing = max(0.04, minimum_support_spacing_cells * 0.50)
    for landmark in landmarks:
        if landmark.x <= start[0] or landmark.x >= end[0]:
            continue
        if any(abs(landmark.x - row[0]) < landmark_spacing for row in knot_rows):
            continue
        knot_rows.append((landmark.x, landmark.y, False))
        used_landmarks.append(landmark)

    # Endpoint circles and endpoint snapping can create a steep final raster
    # step. Place interpolated supports a stable distance inside the branch so
    # a ring edge cannot become a near-vertical boundary Bezier handle.
    if len(target_trace) > 3:
        trace_span = float(end[0] - start[0])
        support_distance = min(
            max(0.18, minimum_support_spacing_cells),
            trace_span / 3.0,
        )
        boundary_supports = (
            np.asarray(
                [
                    float(start[0] + support_distance),
                    float(
                        np.interp(
                            start[0] + support_distance,
                            target_trace[:, 0],
                            target_trace[:, 1],
                        )
                    ),
                ]
            ),
            np.asarray(
                [
                    float(end[0] - support_distance),
                    float(
                        np.interp(
                            end[0] - support_distance,
                            target_trace[:, 0],
                            target_trace[:, 1],
                        )
                    ),
                ]
            ),
        )
        for boundary_neighbor in boundary_supports:
            if any(
                abs(float(boundary_neighbor[0]) - extremum.x) < extremum_shoulder_cells
                for extremum in interior_extrema
            ):
                continue
            if any(
                abs(float(boundary_neighbor[0]) - row[0]) <= 1e-7 for row in knot_rows
            ):
                continue
            knot_rows.append(
                (
                    float(boundary_neighbor[0]),
                    float(boundary_neighbor[1]),
                    False,
                )
            )

    # Keep one trace-derived support point on each side of an extremum. Raster
    # shelves are pulled at least a small distance away from the apex so they
    # cannot turn the extremum into a short horizontal segment.
    shoulder_positions: list[tuple[float, Extremum]] = []
    for extremum in interior_extrema:
        shoulder_positions.extend(
            [
                (extremum.x - extremum_shoulder_cells, extremum),
                (extremum.x + extremum_shoulder_cells, extremum),
            ]
        )
    for shoulder_x, extremum in shoulder_positions:
        if shoulder_x <= start[0] or shoulder_x >= end[0]:
            continue
        if any(
            abs(shoulder_x - row[0]) < minimum_support_spacing_cells
            for row in knot_rows
        ):
            continue
        shoulder_y = float(
            np.interp(shoulder_x, target_trace[:, 0], target_trace[:, 1])
        )
        minimum_relief = 0.12
        if extremum.kind == "maximum":
            shoulder_y = min(shoulder_y, extremum.y - minimum_relief)
        else:
            shoulder_y = max(shoulder_y, extremum.y + minimum_relief)
        knot_rows.append((shoulder_x, shoulder_y, False))

    blocked = np.zeros(len(target_trace), dtype=bool)
    while True:
        knot_rows.sort(key=lambda row: row[0])
        knots = np.asarray([[row[0], row[1]] for row in knot_rows], dtype=np.float64)
        hard_indices = tuple(index for index, row in enumerate(knot_rows) if row[2])
        slopes = _pchip_slopes_with_extrema(
            knots,
            hard_indices,
            smoothing=slope_smoothing,
            extremum_rounding=extremum_rounding,
        )
        fitted_y = _evaluate_hermite(knots, slopes, target_trace[:, 0])
        residual = np.abs(fitted_y - target_trace[:, 1])
        eligible = ~blocked
        for knot_x in knots[:, 0]:
            eligible &= (
                np.abs(target_trace[:, 0] - knot_x) >= minimum_support_spacing_cells
            )
        for extremum in interior_extrema:
            eligible &= (
                np.abs(target_trace[:, 0] - extremum.x) >= extremum_shoulder_cells
            )
        if not np.any(eligible) or len(knots) >= maximum_knots:
            break
        eligible_indices = np.flatnonzero(eligible)
        candidate_index = int(eligible_indices[np.argmax(residual[eligible])])
        if residual[candidate_index] <= maximum_error_cells:
            break

        candidate_x = float(target_trace[candidate_index, 0])
        candidate_y = float(target_trace[candidate_index, 1])
        insertion = int(np.searchsorted(knots[:, 0], candidate_x))
        if insertion <= 0 or insertion >= len(knots):
            blocked[candidate_index] = True
            continue
        if (
            abs(candidate_y - knots[insertion - 1, 1]) < 1e-5
            or abs(candidate_y - knots[insertion, 1]) < 1e-5
        ):
            blocked[candidate_index] = True
            continue
        knot_rows.append((candidate_x, candidate_y, False))

    knot_rows.sort(key=lambda row: row[0])
    knots = np.asarray([[row[0], row[1]] for row in knot_rows], dtype=np.float64)
    hard_indices = tuple(index for index, row in enumerate(knot_rows) if row[2])
    slopes = _pchip_slopes_with_extrema(
        knots,
        hard_indices,
        smoothing=slope_smoothing,
        extremum_rounding=extremum_rounding,
    )
    target_fit = _evaluate_hermite(knots, slopes, target_trace[:, 0])
    original_fit = _evaluate_hermite(knots, slopes, analysis_trace[:, 0])
    target_residual = np.abs(target_fit - target_trace[:, 1])
    constrained_mask = np.ones(len(target_trace), dtype=bool)
    constrained_mask &= target_trace[:, 0] - start[0] >= extremum_shoulder_cells
    constrained_mask &= end[0] - target_trace[:, 0] >= extremum_shoulder_cells
    for extremum in interior_extrema:
        constrained_mask &= (
            np.abs(target_trace[:, 0] - extremum.x) >= extremum_shoulder_cells
        )
    for landmark in used_landmarks:
        constrained_mask &= (
            np.abs(target_trace[:, 0] - landmark.x) >= minimum_support_spacing_cells
        )
    maximum_fit_residual = (
        float(np.max(target_residual[constrained_mask]))
        if np.any(constrained_mask)
        else float(np.max(target_residual))
    )
    return ExtremaFit(
        analysis_trace=target_trace,
        logical_knots=knots,
        slopes=slopes,
        extremum_knot_indices=hard_indices,
        extrema=interior_extrema,
        landmarks=tuple(used_landmarks),
        segment_count=len(knots) - 1,
        maximum_fit_residual=maximum_fit_residual,
        maximum_trace_residual=float(
            np.max(np.abs(original_fit - analysis_trace[:, 1]))
        ),
        slope_smoothing=float(np.clip(slope_smoothing, 0.0, 1.0)),
        extremum_rounding=float(np.clip(extremum_rounding, 0.0, 1.0)),
    )
