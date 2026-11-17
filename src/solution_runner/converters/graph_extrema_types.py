"""Types and coordinate conversion for extrema-based graph fitting."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

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
