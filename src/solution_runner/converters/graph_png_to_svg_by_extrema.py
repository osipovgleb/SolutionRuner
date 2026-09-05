#!/usr/bin/env python3
"""Vectorize raster function graphs by fitting through explicitly detected extrema."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy.interpolate import CubicSpline
from scipy.signal import find_peaks

from . import graph_png_to_svg_by_contrast as base


@dataclass(frozen=True)
class Extremum:
    """Describe one refined and optionally grid-snapped local extremum."""

    kind: str
    raw_x: float
    raw_y: float
    refined_x: float
    refined_y: float
    x: float
    y: float
    prominence: float
    curvature: float
    fit_rmse: float
    confidence: float
    snapped_x: bool
    snapped_y: bool
    grid_evidence_y: float | None
    snapped_y_from_grid_evidence: bool


@dataclass(frozen=True)
class Landmark:
    """Describe an axis crossing or exact lattice node used as a hard curve knot."""

    kinds: tuple[str, ...]
    raw_x: float
    raw_y: float
    x: float
    y: float
    snapped_x: bool
    snapped_y: bool


@dataclass(frozen=True)
class ExtremaFit:
    """Contain the extrema-first logical trace and its Hermite support knots."""

    analysis_trace: np.ndarray
    logical_knots: np.ndarray
    slopes: np.ndarray
    extremum_knot_indices: tuple[int, ...]
    extrema: tuple[Extremum, ...]
    landmarks: tuple[Landmark, ...]
    segment_count: int
    maximum_fit_residual: float
    maximum_trace_residual: float
    slope_smoothing: float
    extremum_rounding: float


def _logical_trace(trace: base.TraceResult, grid: base.GridModel) -> np.ndarray:
    """Convert an extracted source-pixel trace to logical grid coordinates."""
    return np.asarray(
        [base._logical_point(float(x), float(y), grid) for x, y in trace.points],
        dtype=np.float64,
    )


def snap_open_endpoint_centers(
    trace: base.TraceResult,
    grid: base.GridModel,
    *,
    darkness: np.ndarray | None = None,
    y_tolerance_cells: float = 0.65,
    coordinate_quantum: float = 0.5,
    directional_threshold_cells: float = 0.20,
    circle_strength_weight: float = 0.075,
    force_open: bool = False,
) -> base.TraceResult:
    """Recover open-circle centers on the half-cell lattice using branch direction."""

    logical_points = _logical_trace(trace, grid)

    def endpoint_slope(points: np.ndarray) -> float:
        """Estimate the inward branch slope from a short endpoint sample."""
        sample = points[: min(7, len(points))]
        if len(sample) < 2 or float(np.ptp(sample[:, 0])) <= 1e-9:
            return 0.0
        design = np.column_stack([sample[:, 0], np.ones(len(sample))])
        return float(np.linalg.lstsq(design, sample[:, 1], rcond=None)[0][0])

    start_inward_slope = endpoint_slope(logical_points)
    end_inward_slope = endpoint_slope(logical_points[::-1])

    def circle_lattice_strengths(endpoint: base.Endpoint) -> dict[float, int]:
        """Return half-grid y candidates supported by local Hough circles."""
        if darkness is None:
            return {}
        search_radius = max(6, int(round(grid.horizontal.step * 0.80)))
        center_x = int(round(endpoint.pixel_x))
        center_y = int(round(endpoint.pixel_y))
        x_min = max(0, center_x - search_radius)
        x_max = min(darkness.shape[1], center_x + search_radius + 1)
        y_min = max(0, center_y - search_radius)
        y_max = min(darkness.shape[0], center_y + search_radius + 1)
        patch = np.uint8(
            np.clip((1.0 - darkness[y_min:y_max, x_min:x_max]) * 255.0, 0.0, 255.0)
        )
        if min(patch.shape) < 5:
            return {}
        patch = cv2.GaussianBlur(patch, (3, 3), 0.60)
        strengths: dict[float, int] = {}
        maximum_radius = max(3, int(math.ceil(grid.horizontal.step * 0.32)))
        x_tolerance = max(3.0, grid.vertical.step * 0.29)
        quantum = max(1e-6, float(coordinate_quantum))
        lattice_tolerance = min(quantum * 0.46, 0.23)
        for accumulator_threshold in range(10, 1, -1):
            circles = cv2.HoughCircles(
                patch,
                cv2.HOUGH_GRADIENT,
                dp=1.0,
                minDist=2.0,
                param1=80.0,
                param2=float(accumulator_threshold),
                minRadius=1,
                maxRadius=maximum_radius,
            )
            if circles is None:
                continue
            for local_x, local_y, _ in circles[0]:
                pixel_x = float(local_x + x_min)
                pixel_y = float(local_y + y_min)
                if abs(pixel_x - endpoint.pixel_x) > x_tolerance:
                    continue
                logical_y = (grid.horizontal_axis_y - pixel_y) / grid.horizontal.step
                lattice_y = round(logical_y / quantum) * quantum
                if abs(logical_y - lattice_y) > lattice_tolerance:
                    continue
                if abs(lattice_y - endpoint.logical_y) > y_tolerance_cells:
                    continue
                strengths[lattice_y] = max(
                    strengths.get(lattice_y, 0),
                    accumulator_threshold,
                )
        return strengths

    def refined_endpoint(
        endpoint: base.Endpoint,
        *,
        continuation_sign: float,
    ) -> base.Endpoint:
        """Return one endpoint with its open-circle y center grid-corrected."""
        logical_y = float(endpoint.logical_y)
        looks_open = bool(endpoint.looks_open or force_open)
        quantum = max(1e-6, float(coordinate_quantum))
        lower_y = math.floor(logical_y / quantum) * quantum
        upper_y = math.ceil(logical_y / quantum) * quantum
        lower_distance = abs(logical_y - lower_y)
        upper_distance = abs(upper_y - logical_y)
        nearest_y = lower_y if lower_distance <= upper_distance else upper_y
        nearest_distance = min(lower_distance, upper_distance)
        if looks_open:
            if nearest_distance <= 0.05:
                logical_y = nearest_y
            else:
                strengths = circle_lattice_strengths(endpoint)
                if strengths:
                    strengths.setdefault(nearest_y, 0)
                    selected_y = min(
                        strengths,
                        key=lambda candidate: (
                            abs(candidate - logical_y)
                            - circle_strength_weight * strengths[candidate],
                            abs(candidate - logical_y),
                            candidate,
                        ),
                    )
                    logical_y = selected_y
                elif nearest_distance <= y_tolerance_cells:
                    if nearest_distance > directional_threshold_cells:
                        if continuation_sign > 1e-7:
                            nearest_y = upper_y
                        elif continuation_sign < -1e-7:
                            nearest_y = lower_y
                    logical_y = nearest_y
        pixel_y = grid.horizontal_axis_y - logical_y * grid.horizontal.step
        return base.Endpoint(
            pixel_x=float(endpoint.pixel_x),
            pixel_y=float(pixel_y),
            logical_x=float(endpoint.logical_x),
            logical_y=logical_y,
            looks_open=looks_open,
        )

    # At the left boundary the endpoint lies opposite the inward (left-to-right)
    # branch direction; at the right boundary it lies along that direction.
    start = refined_endpoint(
        trace.start,
        continuation_sign=-start_inward_slope,
    )
    end = refined_endpoint(
        trace.end,
        continuation_sign=end_inward_slope,
    )
    points = trace.points.astype(np.float32).copy()
    simplified = trace.simplified_points.astype(np.float32).copy()
    points[0] = (start.pixel_x, start.pixel_y)
    points[-1] = (end.pixel_x, end.pixel_y)
    simplified[0] = points[0]
    simplified[-1] = points[-1]
    return base.TraceResult(
        raw_points=trace.raw_points,
        points=points,
        simplified_points=simplified,
        score=trace.score,
        start=start,
        end=end,
        tangent=trace.tangent,
        vertical_guide=trace.vertical_guide,
        tangent_markers=trace.tangent_markers,
    )


def _smooth_logical_y(
    points: np.ndarray,
    *,
    smoothing_cells: float,
) -> np.ndarray:
    """Smooth logical y values by a grid-scaled Gaussian without moving x values."""
    result = points.astype(np.float64).copy()
    if len(result) < 5 or smoothing_cells <= 0.0:
        return result
    spacing = float(np.median(np.diff(result[:, 0])))
    if spacing <= 1e-9:
        return result
    sigma_samples = max(0.01, smoothing_cells / spacing)
    result[:, 1] = cv2.GaussianBlur(
        result[:, 1].reshape(1, -1),
        (0, 0),
        sigmaX=sigma_samples,
    ).reshape(-1)
    return result


def _refine_extremum(
    points: np.ndarray,
    candidate_index: int,
    *,
    kind: str,
    prominence: float,
    window_cells: float,
    snap_tolerance_cells: float,
    minimum_prominence_cells: float,
    grid_evidence_trace: np.ndarray | None = None,
    grid_evidence_tolerance_cells: float = 0.14,
    grid_evidence_window_cells: float = 0.14,
    grid_evidence_max_correction_cells: float = 0.30,
) -> Extremum:
    """Refine a peak with a local weighted quadratic and conservative grid snapping."""
    raw_x = float(points[candidate_index, 0])
    raw_y = float(points[candidate_index, 1])
    sample_mask = np.abs(points[:, 0] - raw_x) <= window_cells
    sample = points[sample_mask]
    refined_x = raw_x
    refined_y = raw_y
    curvature = 0.0
    fit_rmse = window_cells

    if len(sample) >= 5 and float(np.ptp(sample[:, 0])) > window_cells * 0.65:
        offsets = sample[:, 0] - raw_x
        weights = np.exp(-0.5 * np.square(offsets / max(1e-6, window_cells * 0.58)))
        coefficients = np.polyfit(sample[:, 0], sample[:, 1], 2, w=weights)
        quadratic, linear, constant = (float(value) for value in coefficients)
        expected_curvature = quadratic < -1e-5 if kind == "maximum" else quadratic > 1e-5
        if expected_curvature:
            vertex_x = -linear / (2.0 * quadratic)
            lower = max(float(sample[0, 0]), raw_x - window_cells * 0.80)
            upper = min(float(sample[-1, 0]), raw_x + window_cells * 0.80)
            if lower <= vertex_x <= upper:
                refined_x = float(vertex_x)
                refined_y = float(quadratic * vertex_x**2 + linear * vertex_x + constant)
                curvature = float(2.0 * quadratic)
                fitted = np.polyval(coefficients, sample[:, 0])
                fit_rmse = float(np.sqrt(np.mean(np.square(fitted - sample[:, 1]))))

    raw_nearest_x = float(round(raw_x))
    refined_nearest_x = float(round(refined_x))
    if abs(raw_x - raw_nearest_x) < abs(refined_x - refined_nearest_x):
        nearest_x = raw_nearest_x
        x_grid_distance = abs(raw_x - raw_nearest_x)
    else:
        nearest_x = refined_nearest_x
        x_grid_distance = abs(refined_x - refined_nearest_x)
    raw_nearest_y = float(round(raw_y))
    refined_nearest_y = float(round(refined_y))
    if abs(raw_y - raw_nearest_y) < abs(refined_y - refined_nearest_y):
        nearest_y = raw_nearest_y
        y_grid_distance = abs(raw_y - raw_nearest_y)
    else:
        nearest_y = refined_nearest_y
        y_grid_distance = abs(refined_y - refined_nearest_y)
    # The discrete peak sample can be closer to the true lattice coordinate
    # than an asymmetric local quadratic. Accept grid evidence from either.
    snapped_x = x_grid_distance <= snap_tolerance_cells
    snapped_y = y_grid_distance <= snap_tolerance_cells
    grid_evidence_y: float | None = None
    snapped_y_from_grid_evidence = False
    if grid_evidence_trace is not None and snapped_x:
        evidence_mask = (
            np.abs(grid_evidence_trace[:, 0] - nearest_x)
            <= grid_evidence_window_cells
        )
        evidence_sample = grid_evidence_trace[evidence_mask]
        if len(evidence_sample):
            if kind == "maximum":
                grid_evidence_y = float(np.max(evidence_sample[:, 1]))
            else:
                grid_evidence_y = float(np.min(evidence_sample[:, 1]))
            evidence_nearest_y = float(round(grid_evidence_y))
            evidence_is_close = (
                abs(grid_evidence_y - evidence_nearest_y)
                <= grid_evidence_tolerance_cells
            )
            same_grid_target = evidence_nearest_y == float(round(refined_y))
            correction_is_local = (
                abs(refined_y - evidence_nearest_y)
                <= grid_evidence_max_correction_cells
            )
            smoothing_moved_inward = (
                kind == "maximum"
                and grid_evidence_y >= refined_y - 1e-7
                and evidence_nearest_y >= refined_y - 1e-7
            ) or (
                kind == "minimum"
                and grid_evidence_y <= refined_y + 1e-7
                and evidence_nearest_y <= refined_y + 1e-7
            )
            if (
                not snapped_y
                and evidence_is_close
                and same_grid_target
                and correction_is_local
                and smoothing_moved_inward
            ):
                nearest_y = evidence_nearest_y
                snapped_y = True
                snapped_y_from_grid_evidence = True
    logical_x = nearest_x if snapped_x else refined_x
    logical_y = nearest_y if snapped_y else refined_y

    prominence_score = min(
        1.0,
        prominence / max(1e-6, minimum_prominence_cells * 2.5),
    )
    residual_score = math.exp(-fit_rmse / max(0.04, minimum_prominence_cells))
    curvature_score = min(
        1.0,
        abs(curvature) * window_cells**2 / max(0.08, prominence),
    )
    confidence = float(
        np.clip(
            0.55 * prominence_score + 0.25 * residual_score + 0.20 * curvature_score,
            0.0,
            1.0,
        )
    )
    return Extremum(
        kind=kind,
        raw_x=raw_x,
        raw_y=raw_y,
        refined_x=refined_x,
        refined_y=refined_y,
        x=logical_x,
        y=logical_y,
        prominence=float(prominence),
        curvature=curvature,
        fit_rmse=fit_rmse,
        confidence=confidence,
        snapped_x=snapped_x,
        snapped_y=snapped_y,
        grid_evidence_y=grid_evidence_y,
        snapped_y_from_grid_evidence=snapped_y_from_grid_evidence,
    )


def detect_extrema(
    logical_trace: np.ndarray,
    *,
    grid_evidence_trace: np.ndarray | None = None,
    analysis_smoothing_cells: float = 0.10,
    minimum_prominence_cells: float = 0.18,
    minimum_separation_cells: float = 0.55,
    refinement_window_cells: float = 0.45,
    snap_tolerance_cells: float = 0.18,
    grid_evidence_tolerance_cells: float = 0.14,
    grid_evidence_window_cells: float = 0.14,
    grid_evidence_max_correction_cells: float = 0.30,
) -> tuple[np.ndarray, tuple[Extremum, ...]]:
    """Detect, refine, and grid-snap significant maxima and minima of a trace."""
    if len(logical_trace) < 7:
        return logical_trace.astype(np.float64).copy(), ()
    if np.any(np.diff(logical_trace[:, 0]) <= 0.0):
        raise ValueError("logical_trace_x_must_be_strictly_increasing")
    if grid_evidence_trace is not None:
        grid_evidence_trace = np.asarray(grid_evidence_trace, dtype=np.float64)
        if (
            grid_evidence_trace.ndim != 2
            or grid_evidence_trace.shape[1] != 2
            or np.any(np.diff(grid_evidence_trace[:, 0]) <= 0.0)
        ):
            raise ValueError("grid_evidence_trace_must_be_ordered_xy_points")

    analysis = _smooth_logical_y(
        logical_trace,
        smoothing_cells=analysis_smoothing_cells,
    )
    # Gaussian filtering pulls an open endpoint toward its interior neighbor.
    # Restore the endpoint centers before measuring prominence; otherwise a
    # real near-boundary maximum/minimum can be hidden by the blurred endpoint
    # and later turn into a clipped horizontal shelf.
    analysis[0] = logical_trace[0]
    analysis[-1] = logical_trace[-1]
    sample_spacing = float(np.median(np.diff(analysis[:, 0])))
    minimum_distance = max(1, int(round(minimum_separation_cells / sample_spacing)))
    candidates: list[Extremum] = []
    for values, kind in ((analysis[:, 1], "maximum"), (-analysis[:, 1], "minimum")):
        indices, properties = find_peaks(
            values,
            prominence=max(1e-6, minimum_prominence_cells),
            distance=minimum_distance,
        )
        for index, prominence in zip(indices, properties["prominences"]):
            if (
                analysis[index, 0] - analysis[0, 0] < minimum_separation_cells * 0.45
                or analysis[-1, 0] - analysis[index, 0]
                < minimum_separation_cells * 0.45
            ):
                continue
            candidates.append(
                _refine_extremum(
                    analysis,
                    int(index),
                    kind=kind,
                    prominence=float(prominence),
                    window_cells=refinement_window_cells,
                    snap_tolerance_cells=snap_tolerance_cells,
                    minimum_prominence_cells=minimum_prominence_cells,
                    grid_evidence_trace=grid_evidence_trace,
                    grid_evidence_tolerance_cells=grid_evidence_tolerance_cells,
                    grid_evidence_window_cells=grid_evidence_window_cells,
                    grid_evidence_max_correction_cells=(
                        grid_evidence_max_correction_cells
                    ),
                )
            )

    candidates.sort(key=lambda extremum: extremum.x)
    filtered: list[Extremum] = []
    for candidate in candidates:
        if not filtered or candidate.x - filtered[-1].x >= minimum_separation_cells * 0.55:
            filtered.append(candidate)
            continue
        if candidate.confidence > filtered[-1].confidence:
            filtered[-1] = candidate
    return analysis, tuple(filtered)


def detect_landmarks(
    analysis_trace: np.ndarray,
    extrema: tuple[Extremum, ...],
    *,
    grid_node_tolerance_cells: float = 0.16,
    axis_snap_tolerance_cells: float = 0.18,
    merge_tolerance_cells: float = 0.10,
    extremum_level_exclusion_cells: float = 0.55,
) -> tuple[Landmark, ...]:
    """Detect axis crossings and exact integer lattice nodes along the trace."""
    x_values = analysis_trace[:, 0]
    y_values = analysis_trace[:, 1]
    candidates: list[Landmark] = []

    def append_candidate(
        kinds: tuple[str, ...],
        raw_x: float,
        raw_y: float,
        logical_x: float,
        logical_y: float,
        *,
        snapped_x: bool,
        snapped_y: bool,
    ) -> None:
        """Append one normalized landmark candidate inside the open x-domain."""
        if logical_x <= x_values[0] + 1e-7 or logical_x >= x_values[-1] - 1e-7:
            return
        candidates.append(
            Landmark(
                kinds=tuple(sorted(set(kinds))),
                raw_x=float(raw_x),
                raw_y=float(raw_y),
                x=float(logical_x),
                y=float(logical_y),
                snapped_x=snapped_x,
                snapped_y=snapped_y,
            )
        )

    if x_values[0] < 0.0 < x_values[-1]:
        raw_y = float(np.interp(0.0, x_values, y_values))
        nearest_y = float(round(raw_y))
        snapped_y = abs(raw_y - nearest_y) <= grid_node_tolerance_cells
        append_candidate(
            ("y_axis",),
            0.0,
            raw_y,
            0.0,
            nearest_y if snapped_y else raw_y,
            snapped_x=True,
            snapped_y=snapped_y,
        )

    crossing_x: list[float] = []
    for index in range(len(analysis_trace) - 1):
        left_x = float(x_values[index])
        right_x = float(x_values[index + 1])
        left_y = float(y_values[index])
        right_y = float(y_values[index + 1])
        if abs(left_y) <= 1e-10:
            raw_x = left_x
        elif left_y * right_y < 0.0:
            raw_x = left_x + (right_x - left_x) * (-left_y) / (right_y - left_y)
        else:
            continue
        if crossing_x and abs(raw_x - crossing_x[-1]) <= merge_tolerance_cells:
            continue
        crossing_x.append(raw_x)
        nearest_x = float(round(raw_x))
        snapped_x = abs(raw_x - nearest_x) <= axis_snap_tolerance_cells
        append_candidate(
            ("x_axis",),
            raw_x,
            0.0,
            nearest_x if snapped_x else raw_x,
            0.0,
            snapped_x=snapped_x,
            snapped_y=True,
        )

    first_integer_x = int(math.ceil(float(x_values[0]) - 1e-9))
    last_integer_x = int(math.floor(float(x_values[-1]) + 1e-9))
    for integer_x in range(first_integer_x, last_integer_x + 1):
        raw_y = float(np.interp(float(integer_x), x_values, y_values))
        integer_y = float(round(raw_y))
        if abs(raw_y - integer_y) > grid_node_tolerance_cells:
            continue
        kinds = ["lattice"]
        if integer_x == 0:
            kinds.append("y_axis")
        if integer_y == 0.0:
            kinds.append("x_axis")
        append_candidate(
            tuple(kinds),
            float(integer_x),
            raw_y,
            float(integer_x),
            integer_y,
            snapped_x=True,
            snapped_y=True,
        )

    candidates.sort(key=lambda item: (item.x, item.y, item.kinds))
    merged: list[Landmark] = []
    for candidate in candidates:
        if (
            not merged
            or abs(candidate.x - merged[-1].x) > merge_tolerance_cells
            or abs(candidate.y - merged[-1].y) > grid_node_tolerance_cells * 1.6
        ):
            merged.append(candidate)
            continue
        previous = merged[-1]
        previous_score = int(previous.snapped_x) + int(previous.snapped_y)
        candidate_score = int(candidate.snapped_x) + int(candidate.snapped_y)
        selected = candidate if candidate_score > previous_score else previous
        merged[-1] = Landmark(
            kinds=tuple(sorted(set(previous.kinds + candidate.kinds))),
            raw_x=selected.raw_x,
            raw_y=selected.raw_y,
            x=selected.x,
            y=selected.y,
            snapped_x=previous.snapped_x or candidate.snapped_x,
            snapped_y=previous.snapped_y or candidate.snapped_y,
        )

    # Extrema remain the higher-priority knot when both detectors identify the
    # same feature.  A quantized raster top often makes the neighboring integer
    # x look like an exact lattice node at the extremum's y.  Keeping both
    # points would turn the rounded peak into a short horizontal shelf.
    level_tolerance = min(0.08, grid_node_tolerance_cells * 0.50)
    return tuple(
        landmark
        for landmark in merged
        if not any(
            (
                abs(landmark.x - extremum.x) <= merge_tolerance_cells
                and abs(landmark.y - extremum.y)
                <= grid_node_tolerance_cells * 1.6
            )
            or (
                abs(landmark.x - extremum.x)
                <= extremum_level_exclusion_cells
                and abs(landmark.y - extremum.y) <= level_tolerance
            )
            for extremum in extrema
        )
    )


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
        slopes[1:-1] = (
            (1.0 - amount) * slopes[1:-1]
            + amount * natural_slopes[1:-1]
        )

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
                width = float(
                    points[right_index, 0] - points[left_index, 0]
                )
                if width <= 1e-12:
                    continue
                secant = float(
                    (points[right_index, 1] - points[left_index, 1]) / width
                )
                neighbor_targets.setdefault(neighbor_index, []).append(
                    2.0 * secant
                )
        for neighbor_index, targets in neighbor_targets.items():
            target = float(np.mean(targets))
            slopes[neighbor_index] = (
                (1.0 - rounding) * slopes[neighbor_index]
                + rounding * target
            )

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
    for left, right in zip(hard_points[:-1], hard_points[1:]):
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
        if start[0] + minimum_support_spacing_cells < extremum.x
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
                abs(float(boundary_neighbor[0]) - extremum.x)
                < extremum_shoulder_cells
                for extremum in interior_extrema
            ):
                continue
            if any(
                abs(float(boundary_neighbor[0]) - row[0]) <= 1e-7
                for row in knot_rows
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
            eligible &= np.abs(target_trace[:, 0] - knot_x) >= minimum_support_spacing_cells
        for extremum in interior_extrema:
            eligible &= (
                np.abs(target_trace[:, 0] - extremum.x)
                >= extremum_shoulder_cells
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
    constrained_mask &= (
        target_trace[:, 0] - start[0] >= extremum_shoulder_cells
    )
    constrained_mask &= (
        end[0] - target_trace[:, 0] >= extremum_shoulder_cells
    )
    for extremum in interior_extrema:
        constrained_mask &= (
            np.abs(target_trace[:, 0] - extremum.x)
            >= extremum_shoulder_cells
        )
    for landmark in used_landmarks:
        constrained_mask &= (
            np.abs(target_trace[:, 0] - landmark.x)
            >= minimum_support_spacing_cells
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


def build_extrema_fit(
    trace: base.TraceResult,
    grid: base.GridModel,
    *,
    analysis_smoothing_cells: float,
    minimum_prominence_cells: float,
    minimum_separation_cells: float,
    refinement_window_cells: float,
    extrema_snap_tolerance_cells: float,
    landmark_grid_tolerance_cells: float,
    landmark_axis_snap_tolerance_cells: float,
    maximum_error_cells: float,
    minimum_support_spacing_cells: float,
    extremum_shoulder_cells: float,
    slope_smoothing: float,
    extremum_rounding: float,
    maximum_knots: int,
) -> ExtremaFit:
    """Detect extrema from one extracted trace and construct its v2 curve fit."""
    logical = _logical_trace(trace, grid)
    grid_evidence = np.asarray(
        [
            base._logical_point(float(x), float(y), grid)
            for x, y in trace.raw_points
        ],
        dtype=np.float64,
    )
    analysis, extrema = detect_extrema(
        logical,
        grid_evidence_trace=grid_evidence,
        analysis_smoothing_cells=analysis_smoothing_cells,
        minimum_prominence_cells=minimum_prominence_cells,
        minimum_separation_cells=minimum_separation_cells,
        refinement_window_cells=refinement_window_cells,
        snap_tolerance_cells=extrema_snap_tolerance_cells,
    )
    # Endpoint geometry was already resolved by the base extractor.  Preserve
    # those exact values after the analysis-only Gaussian pass.
    analysis[0] = (trace.start.logical_x, trace.start.logical_y)
    analysis[-1] = (trace.end.logical_x, trace.end.logical_y)
    landmarks = detect_landmarks(
        analysis,
        extrema,
        grid_node_tolerance_cells=landmark_grid_tolerance_cells,
        axis_snap_tolerance_cells=landmark_axis_snap_tolerance_cells,
        extremum_level_exclusion_cells=max(0.55, extremum_shoulder_cells),
    )
    return fit_logical_curve(
        analysis,
        extrema,
        landmarks,
        maximum_error_cells=maximum_error_cells,
        minimum_support_spacing_cells=minimum_support_spacing_cells,
        extremum_shoulder_cells=extremum_shoulder_cells,
        slope_smoothing=slope_smoothing,
        extremum_rounding=extremum_rounding,
        maximum_knots=maximum_knots,
    )


def _extrema_cubic_path(
    fit: ExtremaFit,
    grid: base.GridModel,
    *,
    cell_size: float,
    pad_cells: int,
) -> str:
    """Serialize the extrema-first Hermite fit as cubic SVG path commands."""
    bounds = base._logical_canvas_bounds(grid, max(0, int(pad_cells)))
    mapped = base._logical_points_to_svg(fit.logical_knots, bounds, cell_size)
    mapped_slopes = -fit.slopes
    commands = [f"M{base._fmt(mapped[0, 0])} {base._fmt(mapped[0, 1])}"]
    for index in range(len(mapped) - 1):
        width = float(mapped[index + 1, 0] - mapped[index, 0])
        control_1 = (
            mapped[index, 0] + width / 3.0,
            mapped[index, 1] + mapped_slopes[index] * width / 3.0,
        )
        control_2 = (
            mapped[index + 1, 0] - width / 3.0,
            mapped[index + 1, 1] - mapped_slopes[index + 1] * width / 3.0,
        )
        commands.append(
            "C"
            f"{base._fmt(control_1[0])} {base._fmt(control_1[1])} "
            f"{base._fmt(control_2[0])} {base._fmt(control_2[1])} "
            f"{base._fmt(mapped[index + 1, 0])} {base._fmt(mapped[index + 1, 1])}"
        )
    return " ".join(commands)


def render_extrema_svg(
    grid: base.GridModel,
    trace: base.TraceResult,
    fit: ExtremaFit,
    *,
    cell_size: float,
    pad_cells: int,
    endpoint_style: str,
    include_labels: bool,
    curve_color: str,
    graph_label: str,
) -> str:
    """Reuse the v1 layout while replacing only its curve with the extrema fit."""
    template = base.render_svg(
        grid,
        trace,
        cell_size=cell_size,
        pad_cells=pad_cells,
        path_mode="polyline",
        bezier_error_cells=0.0,
        endpoint_style=endpoint_style,
        include_labels=include_labels,
        curve_color=curve_color,
        graph_label=graph_label,
    )
    mapped_v1 = base._map_points_to_svg(
        trace.simplified_points,
        grid,
        cell_size=cell_size,
        pad_cells=max(0, int(pad_cells)),
    )
    old_path = base._polyline_path(mapped_v1)
    new_path = _extrema_cubic_path(
        fit,
        grid,
        cell_size=cell_size,
        pad_cells=pad_cells,
    )
    old_element = (
        f'  <path d="{old_path}" fill="none" stroke="{curve_color}" stroke-width="1.55"\n'
        '        stroke-linecap="round" stroke-linejoin="round"/>'
    )
    new_element = (
        f'  <path d="{new_path}" fill="none" stroke="{curve_color}" stroke-width="1.55"\n'
        '        stroke-linecap="round" stroke-linejoin="round" '
        'data-fit="extrema-first-v2"/>'
    )
    if template.count(old_element) != 1:
        raise ValueError("base_curve_element_was_not_found_exactly_once")
    return template.replace(old_element, new_element, 1)


def _extremum_payload(extremum: Extremum) -> dict:
    """Convert one extremum to stable JSON diagnostics."""
    return {
        "kind": extremum.kind,
        "raw": [round(extremum.raw_x, 5), round(extremum.raw_y, 5)],
        "refined": [round(extremum.refined_x, 5), round(extremum.refined_y, 5)],
        "logical": [round(extremum.x, 5), round(extremum.y, 5)],
        "snapped": {"x": extremum.snapped_x, "y": extremum.snapped_y},
        "prominence_cells": round(extremum.prominence, 6),
        "curvature": round(extremum.curvature, 6),
        "quadratic_fit_rmse_cells": round(extremum.fit_rmse, 6),
        "confidence": round(extremum.confidence, 6),
        "grid_evidence": {
            "raw_y": (
                round(extremum.grid_evidence_y, 5)
                if extremum.grid_evidence_y is not None
                else None
            ),
            "snapped_y": extremum.snapped_y_from_grid_evidence,
        },
    }


def _landmark_payload(landmark: Landmark) -> dict:
    """Convert one axis/grid landmark to stable JSON diagnostics."""
    return {
        "kinds": list(landmark.kinds),
        "raw": [round(landmark.raw_x, 5), round(landmark.raw_y, 5)],
        "logical": [round(landmark.x, 5), round(landmark.y, 5)],
        "snapped": {"x": landmark.snapped_x, "y": landmark.snapped_y},
    }


def diagnostics_payload(
    source: str,
    rgba: np.ndarray,
    grid: base.GridModel,
    trace: base.TraceResult,
    fit: ExtremaFit,
    *,
    foreground_threshold: float,
) -> dict:
    """Extend the base reproducibility report with extrema-first fit details."""
    payload = base.diagnostics_payload(
        source,
        rgba,
        grid,
        trace,
        foreground_threshold=foreground_threshold,
    )
    payload["algorithm"] = "extrema_first_v2"
    payload["curve"]["extrema"] = [_extremum_payload(item) for item in fit.extrema]
    payload["curve"]["extrema_count"] = len(fit.extrema)
    payload["curve"]["landmarks"] = [
        _landmark_payload(item) for item in fit.landmarks
    ]
    payload["curve"]["landmark_count"] = len(fit.landmarks)
    payload["curve"]["v2_segment_count"] = fit.segment_count
    payload["curve"]["v2_slope_smoothing"] = round(fit.slope_smoothing, 6)
    payload["curve"]["v2_extremum_rounding"] = round(
        fit.extremum_rounding,
        6,
    )
    payload["curve"]["v2_logical_knots"] = base._rounded_points(fit.logical_knots)
    payload["curve"]["v2_extremum_knot_indices"] = list(fit.extremum_knot_indices)
    payload["curve"]["v2_maximum_fit_residual_cells"] = round(
        fit.maximum_fit_residual,
        6,
    )
    payload["curve"]["v2_maximum_trace_residual_cells"] = round(
        fit.maximum_trace_residual,
        6,
    )
    return payload


def save_debug_overlay(
    rgba: np.ndarray,
    grid: base.GridModel,
    trace: base.TraceResult,
    fit: ExtremaFit,
    output: Path,
) -> None:
    """Save the base audit overlay with v2 extrema and support knots marked."""
    base.save_debug_overlay(rgba, grid, trace, output)
    canvas = Image.open(output).convert("RGB")
    draw = ImageDraw.Draw(canvas)
    for index, point in enumerate(fit.logical_knots):
        pixel_x = grid.vertical_axis_x + point[0] * grid.vertical.step
        pixel_y = grid.horizontal_axis_y - point[1] * grid.horizontal.step
        radius = 2 if index not in fit.extremum_knot_indices else 5
        color = (238, 155, 0) if index not in fit.extremum_knot_indices else (210, 30, 150)
        draw.ellipse(
            (pixel_x - radius, pixel_y - radius, pixel_x + radius, pixel_y + radius),
            outline=color,
            width=2,
        )
    for ordinal, extremum in enumerate(fit.extrema, start=1):
        pixel_x = grid.vertical_axis_x + extremum.x * grid.vertical.step
        pixel_y = grid.horizontal_axis_y - extremum.y * grid.horizontal.step
        label = ("max" if extremum.kind == "maximum" else "min") + str(ordinal)
        draw.text((pixel_x + 6, pixel_y - 12), label, fill=(170, 0, 105))
    for landmark in fit.landmarks:
        pixel_x = grid.vertical_axis_x + landmark.x * grid.vertical.step
        pixel_y = grid.horizontal_axis_y - landmark.y * grid.horizontal.step
        radius = 4
        draw.rectangle(
            (
                pixel_x - radius,
                pixel_y - radius,
                pixel_x + radius,
                pixel_y + radius,
            ),
            outline=(0, 125, 210),
            width=2,
        )
    canvas.save(output)


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
    endpoint_snap_tolerance_cells: float,
    open_endpoint_y_tolerance_cells: float,
    open_endpoint_coordinate_quantum: float,
    trace_smoothing_cells: float,
    simplify_cells: float,
    analysis_smoothing_cells: float,
    minimum_prominence_cells: float,
    minimum_separation_cells: float,
    refinement_window_cells: float,
    extrema_snap_tolerance_cells: float,
    landmark_grid_tolerance_cells: float,
    landmark_axis_snap_tolerance_cells: float,
    maximum_error_cells: float,
    minimum_support_spacing_cells: float,
    extremum_shoulder_cells: float,
    slope_smoothing: float,
    extremum_rounding: float,
    maximum_knots: int,
    endpoint_style: str,
    include_labels: bool,
    curve_color: str,
    condition_text: str | None,
    graph_label: str | None,
    x_min: float | None,
    x_max: float | None,
    debug_overlay: bool,
) -> tuple[Path, Path, Path | None]:
    """Extract one raster graph and write the extrema-first SVG and diagnostics."""
    rgba, _ = base.load_image(source)
    resolved_x_interval = base.infer_x_interval(condition_text)
    if (x_min is None) != (x_max is None):
        raise ValueError("--x-min and --x-max must be provided together")
    if x_min is not None and x_max is not None:
        if x_max <= x_min:
            raise ValueError("--x-max must be greater than --x-min")
        resolved_x_interval = base.XInterval(x_min, x_max, True, True)
    if base.infer_graph_kind(condition_text) != "single_curve":
        raise ValueError("extrema_v2_currently_supports_single_curve_diagrams_only")

    darkness, grid, trace = base.extract_graph(
        rgba,
        foreground_threshold=foreground_threshold,
        grid_mask_radius=grid_mask_radius,
        vertical_axis_x=vertical_axis_x,
        horizontal_axis_y=horizontal_axis_y,
        minimum_span_cells=minimum_span_cells,
        snap_tolerance_cells=endpoint_snap_tolerance_cells,
        smoothing_cells=trace_smoothing_cells,
        simplify_cells=simplify_cells,
        x_interval=resolved_x_interval,
    )
    trace = snap_open_endpoint_centers(
        trace,
        grid,
        darkness=darkness,
        y_tolerance_cells=open_endpoint_y_tolerance_cells,
        coordinate_quantum=open_endpoint_coordinate_quantum,
        force_open=endpoint_style == "open",
    )
    fit = build_extrema_fit(
        trace,
        grid,
        analysis_smoothing_cells=analysis_smoothing_cells,
        minimum_prominence_cells=minimum_prominence_cells,
        minimum_separation_cells=minimum_separation_cells,
        refinement_window_cells=refinement_window_cells,
        extrema_snap_tolerance_cells=extrema_snap_tolerance_cells,
        landmark_grid_tolerance_cells=landmark_grid_tolerance_cells,
        landmark_axis_snap_tolerance_cells=landmark_axis_snap_tolerance_cells,
        maximum_error_cells=maximum_error_cells,
        minimum_support_spacing_cells=minimum_support_spacing_cells,
        extremum_shoulder_cells=extremum_shoulder_cells,
        slope_smoothing=slope_smoothing,
        extremum_rounding=extremum_rounding,
        maximum_knots=maximum_knots,
    )
    resolved_graph_label = base.infer_graph_label(condition_text, graph_label)
    svg = render_extrema_svg(
        grid,
        trace,
        fit,
        cell_size=cell_size,
        pad_cells=pad_cells,
        endpoint_style=endpoint_style,
        include_labels=include_labels,
        curve_color=curve_color,
        graph_label=resolved_graph_label,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    asset_id = base.extract_id(source)
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
                fit,
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
        save_debug_overlay(rgba, grid, trace, fit, overlay_path)

    print(f"svg={svg_path}")
    print(f"diagnostics={json_path}")
    if overlay_path is not None:
        print(f"debug_overlay={overlay_path}")
    print(f"algorithm=extrema_first_v2")
    print(f"extrema_count={len(fit.extrema)}")
    print(f"landmark_count={len(fit.landmarks)}")
    print(
        "endpoints="
        f"[({base._fmt(trace.start.logical_x, 4)}, "
        f"{base._fmt(trace.start.logical_y, 4)}), "
        f"({base._fmt(trace.end.logical_x, 4)}, "
        f"{base._fmt(trace.end.logical_y, 4)})]"
    )
    for index, extremum in enumerate(fit.extrema, start=1):
        print(
            f"extremum_{index}={extremum.kind}"
            f"({base._fmt(extremum.x, 4)}, {base._fmt(extremum.y, 4)})"
            f", confidence={base._fmt(extremum.confidence, 3)}"
        )
    print(f"segments={fit.segment_count}")
    print(f"maximum_fit_residual_cells={base._fmt(fit.maximum_fit_residual, 5)}")
    return svg_path, json_path, overlay_path


def main() -> None:
    """Parse CLI options and run the extrema-first graph vectorizer."""
    parser = argparse.ArgumentParser(
        description=(
            "Detect a Cartesian grid and raster trace with the v1 extractor, then "
            "detect extrema as hard knots and fit shape-preserving cubic segments."
        )
    )
    parser.add_argument("source", help="Path or URL to a PNG/JPEG/BMP raster graph")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("graph_svg_from_extrema"),
        help="Output directory for SVG, JSON, and optional debug overlay",
    )
    parser.add_argument("--cell-size", type=float, default=20.0)
    parser.add_argument("--pad-cells", type=int, default=1)
    parser.add_argument("--foreground-threshold", type=float, default=0.20)
    parser.add_argument("--grid-mask-radius", type=int, default=None)
    parser.add_argument("--vertical-axis-x", type=float, default=None)
    parser.add_argument("--horizontal-axis-y", type=float, default=None)
    parser.add_argument("--minimum-span-cells", type=float, default=3.0)
    parser.add_argument(
        "--endpoint-snap-tolerance-cells",
        type=float,
        default=0.22,
        help="Endpoint-to-grid snapping tolerance",
    )
    parser.add_argument(
        "--open-endpoint-y-tolerance-cells",
        type=float,
        default=0.65,
        help="Maximum Hough-supported correction of an open-circle y center",
    )
    parser.add_argument(
        "--open-endpoint-coordinate-quantum",
        type=float,
        default=0.5,
        help="Allowed coordinate step for open-circle centers",
    )
    parser.add_argument(
        "--smoothing-cells",
        type=float,
        default=0.16,
        help="v1 trace smoothing sigma; defaults to the selected third profile",
    )
    parser.add_argument("--simplify-cells", type=float, default=0.035)
    parser.add_argument(
        "--analysis-smoothing-cells",
        type=float,
        default=0.10,
        help="Additional analysis-only smoothing used to locate extrema",
    )
    parser.add_argument(
        "--extrema-prominence-cells",
        type=float,
        default=0.18,
        help="Minimum peak/trough prominence in logical grid cells",
    )
    parser.add_argument(
        "--extrema-min-separation-cells",
        type=float,
        default=0.55,
    )
    parser.add_argument("--extrema-window-cells", type=float, default=0.45)
    parser.add_argument(
        "--extrema-snap-tolerance-cells",
        type=float,
        default=0.18,
        help="Snap a refined extremum coordinate only when this close to a grid line",
    )
    parser.add_argument(
        "--landmark-grid-tolerance-cells",
        type=float,
        default=0.16,
        help="Maximum distance for recognizing an integer lattice node",
    )
    parser.add_argument(
        "--landmark-axis-snap-tolerance-cells",
        type=float,
        default=0.18,
        help="Grid snapping tolerance for OX/OY intersections",
    )
    parser.add_argument(
        "--fit-error-cells",
        "--bezier-error-cells",
        dest="fit_error_cells",
        type=float,
        default=0.08,
        help="Maximum adaptive vertical fitting error in grid cells",
    )
    parser.add_argument("--minimum-support-spacing-cells", type=float, default=0.18)
    parser.add_argument("--extremum-shoulder-cells", type=float, default=0.50)
    parser.add_argument(
        "--slope-smoothing",
        type=float,
        default=0.14,
        help="Small 0..1 blend toward globally smoother knot derivatives",
    )
    parser.add_argument(
        "--extremum-rounding",
        type=float,
        default=0.12,
        help=(
            "Small 0..1 local derivative bias that rounds extrema without "
            "forcing symmetric parabolas"
        ),
    )
    parser.add_argument("--maximum-fit-knots", type=int, default=160)
    parser.add_argument(
        "--endpoint-style",
        choices=("auto", "open", "closed", "none"),
        default="auto",
    )
    parser.add_argument("--no-labels", action="store_true")
    parser.add_argument("--curve-color", default="#143b8f")
    parser.add_argument("--condition-text", default=None)
    parser.add_argument("--graph-label", default=None)
    parser.add_argument("--x-min", type=float, default=None)
    parser.add_argument("--x-max", type=float, default=None)
    parser.add_argument("--debug-overlay", action="store_true")
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
        endpoint_snap_tolerance_cells=args.endpoint_snap_tolerance_cells,
        open_endpoint_y_tolerance_cells=args.open_endpoint_y_tolerance_cells,
        open_endpoint_coordinate_quantum=args.open_endpoint_coordinate_quantum,
        trace_smoothing_cells=args.smoothing_cells,
        simplify_cells=args.simplify_cells,
        analysis_smoothing_cells=args.analysis_smoothing_cells,
        minimum_prominence_cells=args.extrema_prominence_cells,
        minimum_separation_cells=args.extrema_min_separation_cells,
        refinement_window_cells=args.extrema_window_cells,
        extrema_snap_tolerance_cells=args.extrema_snap_tolerance_cells,
        landmark_grid_tolerance_cells=args.landmark_grid_tolerance_cells,
        landmark_axis_snap_tolerance_cells=args.landmark_axis_snap_tolerance_cells,
        maximum_error_cells=args.fit_error_cells,
        minimum_support_spacing_cells=args.minimum_support_spacing_cells,
        extremum_shoulder_cells=args.extremum_shoulder_cells,
        slope_smoothing=args.slope_smoothing,
        extremum_rounding=args.extremum_rounding,
        maximum_knots=args.maximum_fit_knots,
        endpoint_style=args.endpoint_style,
        include_labels=not args.no_labels,
        curve_color=args.curve_color,
        condition_text=args.condition_text,
        graph_label=args.graph_label,
        x_min=args.x_min,
        x_max=args.x_max,
        debug_overlay=args.debug_overlay,
    )


if __name__ == "__main__":
    main()
