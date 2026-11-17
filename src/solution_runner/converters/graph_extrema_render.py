"""Render fitted graph SVG and diagnostics."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from . import graph_png_to_svg_by_contrast as base
from .graph_extrema_types import ExtremaFit, Extremum, Landmark


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
    payload["curve"]["landmarks"] = [_landmark_payload(item) for item in fit.landmarks]
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
        color = (
            (238, 155, 0) if index not in fit.extremum_knot_indices else (210, 30, 150)
        )
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
