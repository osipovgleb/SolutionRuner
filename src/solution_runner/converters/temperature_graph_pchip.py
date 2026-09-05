"""Smooth an already verified temperature trace with bounded PCHIP geometry."""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.interpolate import PchipInterpolator

from .temperature_graph_png_to_svg import TemperatureGraphAnalysis


@dataclass(frozen=True)
class PchipTemperatureCurve:
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
    maximum_deviation_cells: float = 0.15,
) -> PchipTemperatureCurve:
    """Return a shape-preserving PCHIP trace or reject material displacement."""

    points = np.asarray(analysis.curve_points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 20:
        raise ValueError("temperature trace has insufficient PCHIP evidence")
    order = np.argsort(points[:, 0])
    points = points[order]
    if np.any(np.diff(points[:, 0]) <= 0):
        raise ValueError("temperature trace x-coordinates must be unique and increasing")

    anchor_step = analysis.x_grid_step / 5.0
    if anchor_step <= 0 or analysis.y_grid_step <= 0:
        raise ValueError("temperature grid steps must be positive")
    centers = np.arange(points[0, 0], points[-1, 0] + anchor_step * 0.5, anchor_step)
    half_window = anchor_step / 2.0
    anchors: list[tuple[float, float]] = [
        (float(points[0, 0]), float(points[0, 1]))
    ]
    for center in centers:
        if center <= points[0, 0] or center >= points[-1, 0]:
            continue
        local = points[np.abs(points[:, 0] - center) <= half_window]
        if len(local) < 3:
            continue
        anchors.append((float(center), float(np.median(local[:, 1]))))
    anchors.append((float(points[-1, 0]), float(points[-1, 1])))
    if len(anchors) < 5:
        raise ValueError("temperature trace produced too few PCHIP anchors")
    anchor_array = np.asarray(anchors, dtype=np.float64)
    interpolator = PchipInterpolator(anchor_array[:, 0], anchor_array[:, 1], extrapolate=True)
    smoothed_y = np.asarray(interpolator(points[:, 0]), dtype=np.float64)
    displacement = np.abs(smoothed_y - points[:, 1])
    displacement_cells = float(np.max(displacement) / analysis.y_grid_step)
    if displacement_cells > maximum_deviation_cells:
        raise ValueError(
            "PCHIP displacement "
            f"{displacement_cells:.3f} exceeds {maximum_deviation_cells:.3f} grid cells"
        )

    smoothed_points = np.column_stack((points[:, 0], smoothed_y))
    maximum = _daily_maximum(analysis, smoothed_points)
    if maximum != analysis.maximum_temperature:
        raise ValueError(
            f"PCHIP changed daily maximum from {analysis.maximum_temperature} to {maximum}"
        )
    smoothed_analysis = replace(
        analysis,
        curve_points=tuple((float(x), float(y)) for x, y in smoothed_points),
    )
    return PchipTemperatureCurve(
        analysis=smoothed_analysis,
        maximum_deviation_cells=displacement_cells,
        maximum_temperature=maximum,
    )
