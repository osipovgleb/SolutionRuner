"""Apply bounded local smoothing to an already verified temperature trace."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.signal import savgol_filter

from .temperature_graph_png_to_svg import TemperatureGraphAnalysis


@dataclass(frozen=True)
class LocallySmoothedTemperatureCurve:
    """Expose the smoothed analysis and its independently checked displacement."""

    analysis: TemperatureGraphAnalysis
    maximum_deviation_cells: float
    maximum_temperature: int


def _daily_maximum(
    analysis: TemperatureGraphAnalysis,
    points: np.ndarray,
) -> int:
    """Recalculate the requested daily maximum from one candidate trace."""

    day_left = analysis.plot_left + analysis.requested_day_index * 4 * analysis.x_grid_step
    day_right = day_left + 4 * analysis.x_grid_step
    day_curve = points[(points[:, 0] >= day_left) & (points[:, 0] <= day_right)]
    if len(day_curve) < 20:
        raise ValueError("smoothed requested day has insufficient curve evidence")
    peak_y = float(np.percentile(day_curve[:, 1], 1.0))
    maximum = analysis.degrees_per_pixel * peak_y + analysis.temperature_intercept
    rounded = int(round(maximum))
    if abs(maximum - rounded) > 0.30:
        raise ValueError(f"smoothed daily maximum is off the integer scale: {maximum:.3f}")
    return rounded


def smooth_temperature_curve(
    analysis: TemperatureGraphAnalysis,
    *,
    maximum_deviation_cells: float = 0.05,
) -> LocallySmoothedTemperatureCurve:
    """Remove pixel jitter with a five-point filter while preserving verified geometry."""

    points = np.asarray(analysis.curve_points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 20:
        raise ValueError("temperature trace has insufficient smoothing evidence")
    if np.any(np.diff(points[:, 0]) <= 0):
        raise ValueError("temperature trace x-coordinates must be unique and increasing")
    if analysis.y_grid_step <= 0:
        raise ValueError("temperature y-grid step must be positive")

    smoothed_y = np.asarray(
        savgol_filter(points[:, 1], window_length=5, polyorder=2, mode="interp"),
        dtype=np.float64,
    )
    smoothed_y[0] = points[0, 1]
    smoothed_y[-1] = points[-1, 1]
    displacement_cells = float(
        np.max(np.abs(smoothed_y - points[:, 1])) / analysis.y_grid_step
    )
    if displacement_cells > maximum_deviation_cells:
        raise ValueError(
            "local smoothing displacement "
            f"{displacement_cells:.3f} exceeds {maximum_deviation_cells:.3f} grid cells"
        )

    smoothed_points = np.column_stack((points[:, 0], smoothed_y))
    maximum = _daily_maximum(analysis, smoothed_points)
    if maximum != analysis.maximum_temperature:
        raise ValueError(
            "local smoothing changed daily maximum "
            f"from {analysis.maximum_temperature} to {maximum}"
        )
    smoothed_analysis = replace(
        analysis,
        curve_points=tuple((float(x), float(y)) for x, y in smoothed_points),
    )
    return LocallySmoothedTemperatureCurve(
        analysis=smoothed_analysis,
        maximum_deviation_cells=displacement_cells,
        maximum_temperature=maximum,
    )
