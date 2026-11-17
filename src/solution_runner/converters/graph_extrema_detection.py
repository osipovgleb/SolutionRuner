"""Detect graph extrema and landmarks from a logical raster trace."""

from __future__ import annotations

import math

import cv2
import numpy as np
from scipy.signal import find_peaks

from . import graph_extrema_landmarks
from .graph_extrema_types import Extremum

Landmark = graph_extrema_landmarks.Landmark


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


def _nearest_grid_coordinate(
    raw_value: float, refined_value: float
) -> tuple[float, float]:
    """Use whichever estimate lies closer to its nearest grid coordinate."""
    raw_nearest = float(round(raw_value))
    refined_nearest = float(round(refined_value))
    raw_distance = abs(raw_value - raw_nearest)
    refined_distance = abs(refined_value - refined_nearest)
    if raw_distance < refined_distance:
        return raw_nearest, raw_distance
    return refined_nearest, refined_distance


def _quadratic_refinement(points, raw_x, raw_y, kind, window_cells):
    """Fit the local extremum only when its curvature and vertex are plausible."""
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
        expected_curvature = (
            quadratic < -1e-5 if kind == "maximum" else quadratic > 1e-5
        )
        if expected_curvature:
            vertex_x = -linear / (2.0 * quadratic)
            lower = max(float(sample[0, 0]), raw_x - window_cells * 0.80)
            upper = min(float(sample[-1, 0]), raw_x + window_cells * 0.80)
            if lower <= vertex_x <= upper:
                refined_x = float(vertex_x)
                refined_y = float(
                    quadratic * vertex_x**2 + linear * vertex_x + constant
                )
                curvature = float(2.0 * quadratic)
                fitted = np.polyval(coefficients, sample[:, 0])
                fit_rmse = float(np.sqrt(np.mean(np.square(fitted - sample[:, 1]))))

    return refined_x, refined_y, curvature, fit_rmse


def _grid_evidence_adjustment(trace, kind, estimate, tolerances):
    """Use nearby raster evidence to validate an extremum's grid alignment."""
    nearest_x, refined_y, nearest_y, snapped_x, snapped_y = estimate
    (
        grid_evidence_window_cells,
        grid_evidence_tolerance_cells,
        grid_evidence_max_correction_cells,
    ) = tolerances
    grid_evidence_trace = trace
    grid_evidence_y: float | None = None
    snapped_y_from_grid_evidence = False
    if grid_evidence_trace is not None and snapped_x:
        evidence_mask = (
            np.abs(grid_evidence_trace[:, 0] - nearest_x) <= grid_evidence_window_cells
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
    return nearest_y, snapped_y, grid_evidence_y, snapped_y_from_grid_evidence


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
    refined_x, refined_y, curvature, fit_rmse = _quadratic_refinement(
        points, raw_x, raw_y, kind, window_cells
    )

    nearest_x, x_grid_distance = _nearest_grid_coordinate(raw_x, refined_x)
    nearest_y, y_grid_distance = _nearest_grid_coordinate(raw_y, refined_y)
    # The discrete peak sample can be closer to the true lattice coordinate
    # than an asymmetric local quadratic. Accept grid evidence from either.
    snapped_x = x_grid_distance <= snap_tolerance_cells
    snapped_y = y_grid_distance <= snap_tolerance_cells
    nearest_y, snapped_y, grid_evidence_y, snapped_y_from_grid_evidence = (
        _grid_evidence_adjustment(
            grid_evidence_trace,
            kind,
            (nearest_x, refined_y, nearest_y, snapped_x, snapped_y),
            (
                grid_evidence_window_cells,
                grid_evidence_tolerance_cells,
                grid_evidence_max_correction_cells,
            ),
        )
    )
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
    minimum_distance = max(1, round(minimum_separation_cells / sample_spacing))
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
        if (
            not filtered
            or candidate.x - filtered[-1].x >= minimum_separation_cells * 0.55
        ):
            filtered.append(candidate)
            continue
        if candidate.confidence > filtered[-1].confidence:
            filtered[-1] = candidate
    return analysis, tuple(filtered)


_merge_landmarks = graph_extrema_landmarks._merge_landmarks


_axis_crossings = graph_extrema_landmarks._axis_crossings


_lattice_candidates = graph_extrema_landmarks._lattice_candidates


detect_landmarks = graph_extrema_landmarks.detect_landmarks
