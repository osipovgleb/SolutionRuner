"""Refine the source graph endpoint centers before fitting."""

from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np

from . import graph_png_to_svg_by_contrast as base
from .graph_extrema_types import _logical_trace


def _endpoint_slope(points: np.ndarray) -> float:
    """Estimate the inward branch slope from a short endpoint sample."""
    sample = points[: min(7, len(points))]
    if len(sample) < 2 or float(np.ptp(sample[:, 0])) <= 1e-9:
        return 0.0
    design = np.column_stack([sample[:, 0], np.ones(len(sample))])
    return float(np.linalg.lstsq(design, sample[:, 1], rcond=None)[0][0])


@dataclass(frozen=True)
class _EndpointRefiner:
    """Refine endpoint centers using the fitted grid and optional raster."""

    grid: base.GridModel
    darkness: np.ndarray | None
    y_tolerance_cells: float
    coordinate_quantum: float
    directional_threshold_cells: float
    circle_strength_weight: float
    force_open: bool

    def circle_lattice_strengths(self, endpoint: base.Endpoint) -> dict[float, int]:
        """Return half-grid y candidates supported by local Hough circles."""
        grid = self.grid
        darkness = self.darkness
        coordinate_quantum = self.coordinate_quantum
        y_tolerance_cells = self.y_tolerance_cells
        if darkness is None:
            return {}
        search_radius = max(6, round(grid.horizontal.step * 0.80))
        center_x = round(endpoint.pixel_x)
        center_y = round(endpoint.pixel_y)
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
        maximum_radius = max(3, math.ceil(grid.horizontal.step * 0.32))
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
        self,
        endpoint: base.Endpoint,
        *,
        continuation_sign: float,
    ) -> base.Endpoint:
        """Return one endpoint with its open-circle y center grid-corrected."""
        grid = self.grid
        coordinate_quantum = self.coordinate_quantum
        y_tolerance_cells = self.y_tolerance_cells
        directional_threshold_cells = self.directional_threshold_cells
        circle_strength_weight = self.circle_strength_weight
        force_open = self.force_open
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
                strengths = self.circle_lattice_strengths(endpoint)
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

    start_inward_slope = _endpoint_slope(logical_points)
    end_inward_slope = _endpoint_slope(logical_points[::-1])

    # At the left boundary the endpoint lies opposite the inward (left-to-right)
    # branch direction; at the right boundary it lies along that direction.
    refiner = _EndpointRefiner(
        grid,
        darkness,
        y_tolerance_cells,
        coordinate_quantum,
        directional_threshold_cells,
        circle_strength_weight,
        force_open,
    )
    start = refiner.refined_endpoint(
        trace.start,
        continuation_sign=-start_inward_slope,
    )
    end = refiner.refined_endpoint(
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
