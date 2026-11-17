"""Data models used by raster graph extraction."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


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
            indices = [
                round((value - self.origin) / self.step) for value in self.observed
            ]
            first = min(indices)
            last = max(indices)
        else:
            tolerance = max(1.0, self.max_residual + 0.25)
            first = math.ceil((lower_bound - tolerance - self.origin) / self.step)
            last = math.floor((upper_bound + tolerance - self.origin) / self.step)
        return tuple(
            self.origin + index * self.step for index in range(first, last + 1)
        )


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
