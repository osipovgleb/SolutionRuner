"""Select stable support points near extrema and trace boundaries."""

import numpy as np

from .graph_extrema_types import Extremum


def _add_boundary_supports(
    knot_rows, target_trace, endpoints, interior_extrema, spacing
):
    start, end = endpoints
    minimum_support_spacing_cells, extremum_shoulder_cells = spacing
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


def _add_extremum_shoulders(
    knot_rows, target_trace, endpoints, interior_extrema, spacing
):
    start, end = endpoints
    minimum_support_spacing_cells, extremum_shoulder_cells = spacing
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
