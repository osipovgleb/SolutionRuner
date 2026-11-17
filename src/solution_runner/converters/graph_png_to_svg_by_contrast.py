#!/usr/bin/env python3
"""Deterministically recover a Cartesian grid and a dominant function curve from a raster image."""

from __future__ import annotations

import argparse
from pathlib import Path

from . import (
    graph_contrast_diagnostics,
    graph_contrast_extract,
    graph_contrast_grid,
    graph_contrast_models,
    graph_contrast_paths,
    graph_contrast_run,
    graph_contrast_svg,
    graph_contrast_tangent,
    graph_contrast_tangent_svg,
    graph_contrast_trace,
)

extract_id = graph_contrast_run.extract_id
load_image = graph_contrast_run.load_image

GridAxisModel = graph_contrast_models.GridAxisModel


GridModel = graph_contrast_models.GridModel


XInterval = graph_contrast_models.XInterval


Endpoint = graph_contrast_models.Endpoint


TangentLine = graph_contrast_models.TangentLine


VerticalGuide = graph_contrast_models.VerticalGuide


TraceResult = graph_contrast_models.TraceResult


effective_darkness = graph_contrast_grid.effective_darkness


color_aware_curve_evidence = graph_contrast_grid.color_aware_curve_evidence


_group_adjacent = graph_contrast_grid._group_adjacent


projection_line_centers = graph_contrast_grid.projection_line_centers


_step_candidates = graph_contrast_grid._step_candidates


fit_grid_axis = graph_contrast_grid.fit_grid_axis


_line_strength = graph_contrast_grid._line_strength


_detect_axis_line = graph_contrast_grid._detect_axis_line


detect_grid = graph_contrast_grid.detect_grid


grid_pixel_mask = graph_contrast_grid.grid_pixel_mask


_shifted = graph_contrast_tangent._shifted


dominant_curve_path = graph_contrast_extract.dominant_curve_path


detect_tangent_line = graph_contrast_tangent.detect_tangent_line


detect_vertical_tangency_guide = graph_contrast_tangent.detect_vertical_tangency_guide


detect_marked_tangent_grid_points = (
    graph_contrast_tangent.detect_marked_tangent_grid_points
)


_anchored_curve_direction = graph_contrast_tangent._anchored_curve_direction


trace_curve_around_tangent = graph_contrast_tangent.trace_curve_around_tangent


_nearest = graph_contrast_trace._nearest


_logical_point = graph_contrast_trace._logical_point


_large_jump_runs = graph_contrast_trace._large_jump_runs


trim_text_bridge_tails = graph_contrast_trace.trim_text_bridge_tails


_interpolate_or_extrapolate_y = graph_contrast_trace._interpolate_or_extrapolate_y


_endpoint = graph_contrast_trace._endpoint


snap_curve_endpoints = graph_contrast_trace.snap_curve_endpoints


smooth_and_simplify_curve = graph_contrast_trace.smooth_and_simplify_curve


enforce_tangent_contact = graph_contrast_trace.enforce_tangent_contact


extract_graph = graph_contrast_extract.extract_graph


extract_graph_with_tangent = graph_contrast_extract.extract_graph_with_tangent


_fmt = graph_contrast_paths._fmt


_coordinate_label = graph_contrast_svg._coordinate_label


infer_graph_kind = graph_contrast_svg.infer_graph_kind


infer_graph_label = graph_contrast_svg.infer_graph_label


infer_x_interval = graph_contrast_svg.infer_x_interval


_map_points_to_svg = graph_contrast_svg._map_points_to_svg


_polyline_path = graph_contrast_paths._polyline_path


_pchip_slopes = graph_contrast_paths._pchip_slopes


_cubic_path = graph_contrast_paths._cubic_path


_unit_vector = graph_contrast_paths._unit_vector


_bezier_point = graph_contrast_paths._bezier_point


_bezier_derivatives = graph_contrast_paths._bezier_derivatives


_chord_parameters = graph_contrast_paths._chord_parameters


_generate_bezier_segment = graph_contrast_paths._generate_bezier_segment


_maximum_bezier_error = graph_contrast_paths._maximum_bezier_error


_reparameterize_bezier = graph_contrast_paths._reparameterize_bezier


_fit_bezier_recursive = graph_contrast_paths._fit_bezier_recursive


_bezier_path = graph_contrast_paths._bezier_path


_bezier_path_with_fixed_tangent = graph_contrast_paths._bezier_path_with_fixed_tangent


_smooth_function_spline_path = graph_contrast_svg._smooth_function_spline_path


_endpoint_circle_svg = graph_contrast_svg._endpoint_circle_svg


render_svg = graph_contrast_svg.render_svg


_logical_canvas_bounds = graph_contrast_tangent_svg._logical_canvas_bounds


_logical_points_to_svg = graph_contrast_tangent_svg._logical_points_to_svg


_clip_tangent_to_logical_canvas = (
    graph_contrast_tangent_svg._clip_tangent_to_logical_canvas
)


_tangent_lattice_markers = graph_contrast_tangent_svg._tangent_lattice_markers


render_graph_with_tangent_svg = graph_contrast_tangent_svg.render_graph_with_tangent_svg


_rounded_points = graph_contrast_diagnostics._rounded_points


diagnostics_payload = graph_contrast_diagnostics.diagnostics_payload


save_debug_overlay = graph_contrast_diagnostics.save_debug_overlay


run = graph_contrast_run.run


def main() -> None:
    """Parse CLI options and run the deterministic graph vectorizer."""
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically detect a Cartesian grid, suppress it, trace the dominant "
            "function curve by contrast, and render a normalized SVG."
        )
    )
    parser.add_argument("source", help="Path or URL to a PNG/JPEG/BMP raster graph")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("graph_svg_from_contrast"),
        help="Output directory for SVG, JSON, and optional debug overlay",
    )
    parser.add_argument(
        "--cell-size", type=float, default=20.0, help="SVG grid cell size"
    )
    parser.add_argument(
        "--pad-cells",
        type=int,
        default=1,
        help="Extra grid cells around the source grid",
    )
    parser.add_argument(
        "--foreground-threshold",
        type=float,
        default=0.20,
        help="Visible-darkness threshold used only for long grid-line detection",
    )
    parser.add_argument(
        "--grid-mask-radius",
        type=int,
        default=None,
        help="Pixels removed around every detected grid line; default is scale-dependent",
    )
    parser.add_argument(
        "--vertical-axis-x",
        type=float,
        default=None,
        help="Override the automatically detected y-axis x position in source pixels",
    )
    parser.add_argument(
        "--horizontal-axis-y",
        type=float,
        default=None,
        help="Override the automatically detected x-axis y position in source pixels",
    )
    parser.add_argument(
        "--minimum-span-cells",
        type=float,
        default=3.0,
        help="Reject traces shorter than this many grid cells",
    )
    parser.add_argument(
        "--snap-tolerance-cells",
        type=float,
        default=0.22,
        help="Endpoint-to-grid snapping tolerance measured in cells",
    )
    parser.add_argument(
        "--smoothing-cells",
        type=float,
        default=0.030,
        help="Gaussian trace smoothing sigma measured in cells",
    )
    parser.add_argument(
        "--simplify-cells",
        type=float,
        default=0.035,
        help="Curve-knot simplification tolerance measured in cells",
    )
    parser.add_argument(
        "--path-mode",
        choices=("bezier", "cubic", "polyline"),
        default="bezier",
        help="Render adaptive Bezier fitting, shape-preserving cubic knots, or a polyline",
    )
    parser.add_argument(
        "--bezier-error-cells",
        type=float,
        default=0.030,
        help="Maximum adaptive Bezier fitting error measured in grid cells",
    )
    parser.add_argument(
        "--endpoint-style",
        choices=("auto", "open", "closed", "none"),
        default="auto",
        help="Endpoint rendering; auto draws circles only when ring overhang is detected",
    )
    parser.add_argument(
        "--no-labels", action="store_true", help="Omit coordinate labels and ticks"
    )
    parser.add_argument(
        "--curve-color", default="#143b8f", help="SVG curve stroke color"
    )
    parser.add_argument(
        "--condition-text",
        default=None,
        help="Condition text used to infer y=f(x), y=f′(x), y=f″(x), or y=F(x)",
    )
    parser.add_argument(
        "--graph-label",
        default=None,
        help="Explicit SVG graph label; overrides --condition-text inference",
    )
    parser.add_argument(
        "--diagram-kind",
        choices=("auto", "single_curve", "function_with_tangent"),
        default="auto",
        help="Extractor selection; auto routes from the condition text",
    )
    parser.add_argument(
        "--x-min", type=float, default=None, help="Explicit logical left x bound"
    )
    parser.add_argument(
        "--x-max", type=float, default=None, help="Explicit logical right x bound"
    )
    parser.add_argument(
        "--debug-overlay",
        action="store_true",
        help="Also save a raster overlay of detected grid, axes, trace, and endpoints",
    )
    args = parser.parse_args()

    run(
        args.source,
        args.out_dir,
        cell_size=args.cell_size,
        pad_cells=args.pad_cells,
        foreground_threshold=args.foreground_threshold,
        grid_mask_radius=args.grid_mask_radius,
        vertical_axis_x=args.vertical_axis_x,
        horizontal_axis_y=args.horizontal_axis_y,
        minimum_span_cells=args.minimum_span_cells,
        snap_tolerance_cells=args.snap_tolerance_cells,
        smoothing_cells=args.smoothing_cells,
        simplify_cells=args.simplify_cells,
        path_mode=args.path_mode,
        bezier_error_cells=args.bezier_error_cells,
        endpoint_style=args.endpoint_style,
        include_labels=not args.no_labels,
        curve_color=args.curve_color,
        condition_text=args.condition_text,
        graph_label=args.graph_label,
        diagram_kind=args.diagram_kind,
        x_min=args.x_min,
        x_max=args.x_max,
        debug_overlay=args.debug_overlay,
    )


if __name__ == "__main__":
    main()
