"""Compose detection and fitting for one extracted graph trace."""

from __future__ import annotations

import numpy as np

from . import graph_png_to_svg_by_contrast as base
from .graph_extrema_detection import detect_extrema, detect_landmarks
from .graph_extrema_fit import fit_logical_curve
from .graph_extrema_types import ExtremaFit, _logical_trace


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
        [base._logical_point(float(x), float(y), grid) for x, y in trace.raw_points],
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
