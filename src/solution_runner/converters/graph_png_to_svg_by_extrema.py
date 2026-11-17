#!/usr/bin/env python3
"""Vectorize raster function graphs by fitting through explicitly detected extrema."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import graph_extrema_analysis as _part4
from . import graph_extrema_detection as _part2
from . import graph_extrema_endpoints as _part1
from . import graph_extrema_fit as _part3
from . import graph_extrema_render as _part5
from . import graph_extrema_types as _part0
from . import graph_png_to_svg_by_contrast as base

Extremum = _part0.Extremum
Landmark = _part0.Landmark
ExtremaFit = _part0.ExtremaFit
_logical_trace = _part0._logical_trace
snap_open_endpoint_centers = _part1.snap_open_endpoint_centers
_smooth_logical_y = _part2._smooth_logical_y
_refine_extremum = _part2._refine_extremum
detect_extrema = _part2.detect_extrema
detect_landmarks = _part2.detect_landmarks
_pchip_slopes_with_extrema = _part3._pchip_slopes_with_extrema
_evaluate_hermite = _part3._evaluate_hermite
_project_between_extrema = _part3._project_between_extrema
fit_logical_curve = _part3.fit_logical_curve
build_extrema_fit = _part4.build_extrema_fit
_extrema_cubic_path = _part5._extrema_cubic_path
render_extrema_svg = _part5.render_extrema_svg
_extremum_payload = _part5._extremum_payload
_landmark_payload = _part5._landmark_payload
diagnostics_payload = _part5.diagnostics_payload
save_debug_overlay = _part5.save_debug_overlay


def run(
    source: str,
    out_dir: Path,
    *,
    cell_size: float,
    pad_cells: int,
    foreground_threshold: float,
    grid_mask_radius: int | None,
    vertical_axis_x: float | None,
    horizontal_axis_y: float | None,
    minimum_span_cells: float,
    endpoint_snap_tolerance_cells: float,
    open_endpoint_y_tolerance_cells: float,
    open_endpoint_coordinate_quantum: float,
    trace_smoothing_cells: float,
    simplify_cells: float,
    analysis_smoothing_cells: float,
    minimum_prominence_cells: float,
    minimum_separation_cells: float,
    refinement_window_cells: float,
    extrema_snap_tolerance_cells: float,
    landmark_grid_tolerance_cells: float,
    landmark_axis_snap_tolerance_cells: float,
    maximum_error_cells: float,
    minimum_support_spacing_cells: float,
    extremum_shoulder_cells: float,
    slope_smoothing: float,
    extremum_rounding: float,
    maximum_knots: int,
    endpoint_style: str,
    include_labels: bool,
    curve_color: str,
    condition_text: str | None,
    graph_label: str | None,
    x_min: float | None,
    x_max: float | None,
    debug_overlay: bool,
) -> tuple[Path, Path, Path | None]:
    """Extract one raster graph and write the extrema-first SVG and diagnostics."""
    rgba, _ = base.load_image(source)
    resolved_x_interval = base.infer_x_interval(condition_text)
    if (x_min is None) != (x_max is None):
        raise ValueError("--x-min and --x-max must be provided together")
    if x_min is not None and x_max is not None:
        if x_max <= x_min:
            raise ValueError("--x-max must be greater than --x-min")
        resolved_x_interval = base.XInterval(x_min, x_max, True, True)
    if base.infer_graph_kind(condition_text) != "single_curve":
        raise ValueError("extrema_v2_currently_supports_single_curve_diagrams_only")

    darkness, grid, trace = base.extract_graph(
        rgba,
        foreground_threshold=foreground_threshold,
        grid_mask_radius=grid_mask_radius,
        vertical_axis_x=vertical_axis_x,
        horizontal_axis_y=horizontal_axis_y,
        minimum_span_cells=minimum_span_cells,
        snap_tolerance_cells=endpoint_snap_tolerance_cells,
        smoothing_cells=trace_smoothing_cells,
        simplify_cells=simplify_cells,
        x_interval=resolved_x_interval,
    )
    trace = snap_open_endpoint_centers(
        trace,
        grid,
        darkness=darkness,
        y_tolerance_cells=open_endpoint_y_tolerance_cells,
        coordinate_quantum=open_endpoint_coordinate_quantum,
        force_open=endpoint_style == "open",
    )
    fit = build_extrema_fit(
        trace,
        grid,
        analysis_smoothing_cells=analysis_smoothing_cells,
        minimum_prominence_cells=minimum_prominence_cells,
        minimum_separation_cells=minimum_separation_cells,
        refinement_window_cells=refinement_window_cells,
        extrema_snap_tolerance_cells=extrema_snap_tolerance_cells,
        landmark_grid_tolerance_cells=landmark_grid_tolerance_cells,
        landmark_axis_snap_tolerance_cells=landmark_axis_snap_tolerance_cells,
        maximum_error_cells=maximum_error_cells,
        minimum_support_spacing_cells=minimum_support_spacing_cells,
        extremum_shoulder_cells=extremum_shoulder_cells,
        slope_smoothing=slope_smoothing,
        extremum_rounding=extremum_rounding,
        maximum_knots=maximum_knots,
    )
    resolved_graph_label = base.infer_graph_label(condition_text, graph_label)
    svg = render_extrema_svg(
        grid,
        trace,
        fit,
        cell_size=cell_size,
        pad_cells=pad_cells,
        endpoint_style=endpoint_style,
        include_labels=include_labels,
        curve_color=curve_color,
        graph_label=resolved_graph_label,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    asset_id = base.extract_id(source)
    svg_path = out_dir / f"{asset_id}.svg"
    json_path = out_dir / f"{asset_id}.json"
    overlay_path = out_dir / f"{asset_id}.debug.png" if debug_overlay else None
    svg_path.write_text(svg, encoding="utf-8")
    json_path.write_text(
        json.dumps(
            diagnostics_payload(
                source,
                rgba,
                grid,
                trace,
                fit,
                foreground_threshold=foreground_threshold,
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    if overlay_path is not None:
        save_debug_overlay(rgba, grid, trace, fit, overlay_path)

    print(f"svg={svg_path}")
    print(f"diagnostics={json_path}")
    if overlay_path is not None:
        print(f"debug_overlay={overlay_path}")
    print("algorithm=extrema_first_v2")
    print(f"extrema_count={len(fit.extrema)}")
    print(f"landmark_count={len(fit.landmarks)}")
    print(
        "endpoints="
        f"[({base._fmt(trace.start.logical_x, 4)}, "
        f"{base._fmt(trace.start.logical_y, 4)}), "
        f"({base._fmt(trace.end.logical_x, 4)}, "
        f"{base._fmt(trace.end.logical_y, 4)})]"
    )
    for index, extremum in enumerate(fit.extrema, start=1):
        print(
            f"extremum_{index}={extremum.kind}"
            f"({base._fmt(extremum.x, 4)}, {base._fmt(extremum.y, 4)})"
            f", confidence={base._fmt(extremum.confidence, 3)}"
        )
    print(f"segments={fit.segment_count}")
    print(f"maximum_fit_residual_cells={base._fmt(fit.maximum_fit_residual, 5)}")
    return svg_path, json_path, overlay_path


def main() -> None:
    """Parse CLI options and run the extrema-first graph vectorizer."""
    parser = argparse.ArgumentParser(
        description=(
            "Detect a Cartesian grid and raster trace with the v1 extractor, then "
            "detect extrema as hard knots and fit shape-preserving cubic segments."
        )
    )
    parser.add_argument("source", help="Path or URL to a PNG/JPEG/BMP raster graph")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("graph_svg_from_extrema"),
        help="Output directory for SVG, JSON, and optional debug overlay",
    )
    parser.add_argument("--cell-size", type=float, default=20.0)
    parser.add_argument("--pad-cells", type=int, default=1)
    parser.add_argument("--foreground-threshold", type=float, default=0.20)
    parser.add_argument("--grid-mask-radius", type=int, default=None)
    parser.add_argument("--vertical-axis-x", type=float, default=None)
    parser.add_argument("--horizontal-axis-y", type=float, default=None)
    parser.add_argument("--minimum-span-cells", type=float, default=3.0)
    parser.add_argument(
        "--endpoint-snap-tolerance-cells",
        type=float,
        default=0.22,
        help="Endpoint-to-grid snapping tolerance",
    )
    parser.add_argument(
        "--open-endpoint-y-tolerance-cells",
        type=float,
        default=0.65,
        help="Maximum Hough-supported correction of an open-circle y center",
    )
    parser.add_argument(
        "--open-endpoint-coordinate-quantum",
        type=float,
        default=0.5,
        help="Allowed coordinate step for open-circle centers",
    )
    parser.add_argument(
        "--smoothing-cells",
        type=float,
        default=0.16,
        help="v1 trace smoothing sigma; defaults to the selected third profile",
    )
    parser.add_argument("--simplify-cells", type=float, default=0.035)
    parser.add_argument(
        "--analysis-smoothing-cells",
        type=float,
        default=0.10,
        help="Additional analysis-only smoothing used to locate extrema",
    )
    parser.add_argument(
        "--extrema-prominence-cells",
        type=float,
        default=0.18,
        help="Minimum peak/trough prominence in logical grid cells",
    )
    parser.add_argument(
        "--extrema-min-separation-cells",
        type=float,
        default=0.55,
    )
    parser.add_argument("--extrema-window-cells", type=float, default=0.45)
    parser.add_argument(
        "--extrema-snap-tolerance-cells",
        type=float,
        default=0.18,
        help="Snap a refined extremum coordinate only when this close to a grid line",
    )
    parser.add_argument(
        "--landmark-grid-tolerance-cells",
        type=float,
        default=0.16,
        help="Maximum distance for recognizing an integer lattice node",
    )
    parser.add_argument(
        "--landmark-axis-snap-tolerance-cells",
        type=float,
        default=0.18,
        help="Grid snapping tolerance for OX/OY intersections",
    )
    parser.add_argument(
        "--fit-error-cells",
        "--bezier-error-cells",
        dest="fit_error_cells",
        type=float,
        default=0.08,
        help="Maximum adaptive vertical fitting error in grid cells",
    )
    parser.add_argument("--minimum-support-spacing-cells", type=float, default=0.18)
    parser.add_argument("--extremum-shoulder-cells", type=float, default=0.50)
    parser.add_argument(
        "--slope-smoothing",
        type=float,
        default=0.14,
        help="Small 0..1 blend toward globally smoother knot derivatives",
    )
    parser.add_argument(
        "--extremum-rounding",
        type=float,
        default=0.12,
        help=(
            "Small 0..1 local derivative bias that rounds extrema without "
            "forcing symmetric parabolas"
        ),
    )
    parser.add_argument("--maximum-fit-knots", type=int, default=160)
    parser.add_argument(
        "--endpoint-style",
        choices=("auto", "open", "closed", "none"),
        default="auto",
    )
    parser.add_argument("--no-labels", action="store_true")
    parser.add_argument("--curve-color", default="#143b8f")
    parser.add_argument("--condition-text", default=None)
    parser.add_argument("--graph-label", default=None)
    parser.add_argument("--x-min", type=float, default=None)
    parser.add_argument("--x-max", type=float, default=None)
    parser.add_argument("--debug-overlay", action="store_true")
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
        endpoint_snap_tolerance_cells=args.endpoint_snap_tolerance_cells,
        open_endpoint_y_tolerance_cells=args.open_endpoint_y_tolerance_cells,
        open_endpoint_coordinate_quantum=args.open_endpoint_coordinate_quantum,
        trace_smoothing_cells=args.smoothing_cells,
        simplify_cells=args.simplify_cells,
        analysis_smoothing_cells=args.analysis_smoothing_cells,
        minimum_prominence_cells=args.extrema_prominence_cells,
        minimum_separation_cells=args.extrema_min_separation_cells,
        refinement_window_cells=args.extrema_window_cells,
        extrema_snap_tolerance_cells=args.extrema_snap_tolerance_cells,
        landmark_grid_tolerance_cells=args.landmark_grid_tolerance_cells,
        landmark_axis_snap_tolerance_cells=args.landmark_axis_snap_tolerance_cells,
        maximum_error_cells=args.fit_error_cells,
        minimum_support_spacing_cells=args.minimum_support_spacing_cells,
        extremum_shoulder_cells=args.extremum_shoulder_cells,
        slope_smoothing=args.slope_smoothing,
        extremum_rounding=args.extremum_rounding,
        maximum_knots=args.maximum_fit_knots,
        endpoint_style=args.endpoint_style,
        include_labels=not args.no_labels,
        curve_color=args.curve_color,
        condition_text=args.condition_text,
        graph_label=args.graph_label,
        x_min=args.x_min,
        x_max=args.x_max,
        debug_overlay=args.debug_overlay,
    )


if __name__ == "__main__":
    main()
