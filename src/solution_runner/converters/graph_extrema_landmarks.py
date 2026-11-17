"""Find axis crossings and lattice landmarks on recovered graph traces."""

from __future__ import annotations

import math

import numpy as np

from .graph_extrema_types import Extremum, Landmark


def _merge_landmarks(
    candidates,
    extrema,
    merge_tolerance_cells,
    grid_node_tolerance_cells,
    extremum_level_exclusion_cells,
):
    """Merge nearby landmarks and keep extrema as higher-priority knots."""
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
                and abs(landmark.y - extremum.y) <= grid_node_tolerance_cells * 1.6
            )
            or (
                abs(landmark.x - extremum.x) <= extremum_level_exclusion_cells
                and abs(landmark.y - extremum.y) <= level_tolerance
            )
            for extremum in extrema
        )
    )


def _axis_crossings(x_values, y_values, merge_tolerance_cells):
    """Locate distinct x-axis crossings on the sampled curve."""
    crossing_x: list[float] = []
    for index in range(len(x_values) - 1):
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
    return crossing_x


def _lattice_candidates(x_values, y_values, grid_node_tolerance_cells):
    """Yield integer-grid points supported by the sampled curve."""
    first_integer_x = math.ceil(float(x_values[0]) - 1e-9)
    last_integer_x = math.floor(float(x_values[-1]) + 1e-9)
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
        yield (
            tuple(kinds),
            float(integer_x),
            raw_y,
            float(integer_x),
            integer_y,
        )


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
        raw_point: tuple[float, float],
        logical_point: tuple[float, float],
        *,
        snapped_x: bool,
        snapped_y: bool,
    ) -> None:
        """Append one normalized landmark candidate inside the open x-domain."""
        raw_x, raw_y = raw_point
        logical_x, logical_y = logical_point
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
            (0.0, raw_y),
            (0.0, nearest_y if snapped_y else raw_y),
            snapped_x=True,
            snapped_y=snapped_y,
        )

    for raw_x in _axis_crossings(x_values, y_values, merge_tolerance_cells):
        nearest_x = float(round(raw_x))
        snapped_x = abs(raw_x - nearest_x) <= axis_snap_tolerance_cells
        append_candidate(
            ("x_axis",),
            (raw_x, 0.0),
            (nearest_x if snapped_x else raw_x, 0.0),
            snapped_x=snapped_x,
            snapped_y=True,
        )

    for kinds, raw_x, raw_y, logical_x, logical_y in _lattice_candidates(
        x_values, y_values, grid_node_tolerance_cells
    ):
        append_candidate(
            kinds,
            (raw_x, raw_y),
            (logical_x, logical_y),
            snapped_x=True,
            snapped_y=True,
        )

    return _merge_landmarks(
        candidates,
        extrema,
        merge_tolerance_cells,
        grid_node_tolerance_cells,
        extremum_level_exclusion_cells,
    )
