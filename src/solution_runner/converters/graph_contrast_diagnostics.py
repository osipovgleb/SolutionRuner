"""Prepare graph extraction diagnostics and debug overlays."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .graph_contrast_models import GridModel, TraceResult
from .graph_contrast_trace import _logical_point


def _rounded_points(points: np.ndarray, digits: int = 4) -> list[list[float]]:
    """Convert a NumPy point array to stable JSON-ready rounded values."""
    return [[round(float(x), digits), round(float(y), digits)] for x, y in points]


def diagnostics_payload(
    source: str,
    rgba: np.ndarray,
    grid: GridModel,
    trace: TraceResult,
    *,
    foreground_threshold: float,
) -> dict:
    """Build the reproducibility report saved beside the generated SVG."""
    logical_knots = np.asarray(
        [_logical_point(float(x), float(y), grid) for x, y in trace.simplified_points],
        dtype=np.float64,
    )
    payload = {
        "source": source,
        "image": {"width": int(rgba.shape[1]), "height": int(rgba.shape[0])},
        "foreground_threshold": float(foreground_threshold),
        "grid": {
            "vertical_lines": [round(value, 6) for value in grid.vertical_lines()],
            "horizontal_lines": [round(value, 6) for value in grid.horizontal_lines()],
            "vertical_step": round(grid.vertical.step, 6),
            "horizontal_step": round(grid.horizontal.step, 6),
            "vertical_max_residual": round(grid.vertical.max_residual, 6),
            "horizontal_max_residual": round(grid.horizontal.max_residual, 6),
            "vertical_axis_x": round(grid.vertical_axis_x, 6),
            "horizontal_axis_y": round(grid.horizontal_axis_y, 6),
            "grid_mask_radius": int(grid.grid_mask_radius),
            "detection_threshold": round(grid.detection_threshold, 6),
        },
        "curve": {
            "trace_score": round(trace.score, 6),
            "raw_span_pixels": round(
                float(trace.raw_points[-1, 0] - trace.raw_points[0, 0]), 6
            ),
            "raw_point_count": len(trace.raw_points),
            "simplified_point_count": len(trace.simplified_points),
            "pixel_knots": _rounded_points(trace.simplified_points),
            "logical_knots": _rounded_points(logical_knots),
            "start": {
                "pixel": [round(trace.start.pixel_x, 4), round(trace.start.pixel_y, 4)],
                "logical": [
                    round(trace.start.logical_x, 4),
                    round(trace.start.logical_y, 4),
                ],
                "looks_open": bool(trace.start.looks_open),
            },
            "end": {
                "pixel": [round(trace.end.pixel_x, 4), round(trace.end.pixel_y, 4)],
                "logical": [
                    round(trace.end.logical_x, 4),
                    round(trace.end.logical_y, 4),
                ],
                "looks_open": bool(trace.end.looks_open),
            },
        },
    }
    if trace.tangent is not None:
        payload["tangent"] = {
            "pixel_line": {
                "slope": round(trace.tangent.slope, 8),
                "intercept": round(trace.tangent.intercept, 8),
                "start_x": round(trace.tangent.start_x, 4),
                "end_x": round(trace.tangent.end_x, 4),
            },
            "logical_slope": round(trace.tangent.logical_slope, 8),
            "logical_intercept": round(trace.tangent.logical_intercept, 8),
            "support_pixels": int(trace.tangent.support_pixels),
        }
        if trace.tangent_markers is not None:
            payload["tangent"]["marked_lattice_points"] = _rounded_points(
                trace.tangent_markers
            )
    if trace.vertical_guide is not None:
        payload["vertical_guide"] = {
            "pixel_x": round(trace.vertical_guide.pixel_x, 4),
            "start_y": round(trace.vertical_guide.start_y, 4),
            "end_y": round(trace.vertical_guide.end_y, 4),
            "label": trace.vertical_guide.label,
        }
    return payload


def save_debug_overlay(
    rgba: np.ndarray,
    grid: GridModel,
    trace: TraceResult,
    output: Path,
) -> None:
    """Save a visual audit overlay without affecting extraction decisions."""
    source = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
    canvas = Image.new("RGBA", source.size, (255, 255, 255, 255))
    canvas.alpha_composite(source)
    draw = ImageDraw.Draw(canvas)
    width, height = canvas.size
    for x in grid.vertical_lines():
        draw.line((x, 0, x, height - 1), fill=(0, 170, 190, 150), width=1)
    for y in grid.horizontal_lines():
        draw.line((0, y, width - 1, y), fill=(0, 170, 190, 150), width=1)
    draw.line(
        (grid.vertical_axis_x, 0, grid.vertical_axis_x, height - 1),
        fill=(225, 50, 50, 220),
        width=2,
    )
    draw.line(
        (0, grid.horizontal_axis_y, width - 1, grid.horizontal_axis_y),
        fill=(225, 50, 50, 220),
        width=2,
    )
    if trace.tangent is not None:
        draw.line(
            (
                trace.tangent.start_x,
                trace.tangent.y_at(trace.tangent.start_x),
                trace.tangent.end_x,
                trace.tangent.y_at(trace.tangent.end_x),
            ),
            fill=(235, 120, 20, 255),
            width=2,
        )
    if trace.vertical_guide is not None:
        draw.line(
            (
                trace.vertical_guide.pixel_x,
                trace.vertical_guide.start_y,
                trace.vertical_guide.pixel_x,
                trace.vertical_guide.end_y,
            ),
            fill=(150, 40, 180, 255),
            width=2,
        )
    draw.line(
        [tuple(map(float, point)) for point in trace.points],
        fill=(20, 80, 220, 255),
        width=2,
    )
    radius = 3
    for endpoint in (trace.start, trace.end):
        draw.ellipse(
            (
                endpoint.pixel_x - radius,
                endpoint.pixel_y - radius,
                endpoint.pixel_x + radius,
                endpoint.pixel_y + radius,
            ),
            outline=(0, 150, 40, 255),
            width=2,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output)
