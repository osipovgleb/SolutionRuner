"""Run graph extraction and write its output files."""

from __future__ import annotations

import json
from pathlib import Path

from .graph_contrast_diagnostics import diagnostics_payload, save_debug_overlay
from .graph_contrast_extract import extract_graph, extract_graph_with_tangent
from .graph_contrast_models import XInterval
from .graph_contrast_report import report_outputs
from .graph_contrast_svg import (
    infer_graph_kind,
    infer_graph_label,
    infer_x_interval,
    render_svg,
)
from .graph_contrast_tangent_svg import render_graph_with_tangent_svg
from .png_to_svg_by_contrast import extract_id, load_image


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
    snap_tolerance_cells: float,
    smoothing_cells: float,
    simplify_cells: float,
    path_mode: str,
    bezier_error_cells: float,
    endpoint_style: str,
    include_labels: bool,
    curve_color: str,
    condition_text: str | None,
    graph_label: str | None,
    diagram_kind: str | None,
    x_min: float | None,
    x_max: float | None,
    debug_overlay: bool,
) -> tuple[Path, Path, Path | None]:
    """Extract one raster graph and write its SVG and deterministic diagnostics."""
    rgba, _ = load_image(source)
    resolved_x_interval = infer_x_interval(condition_text)
    if (x_min is None) != (x_max is None):
        raise ValueError("--x-min and --x-max must be provided together")
    if x_min is not None and x_max is not None:
        if x_max <= x_min:
            raise ValueError("--x-max must be greater than --x-min")
        resolved_x_interval = XInterval(x_min, x_max, True, True)
    resolved_diagram_kind = infer_graph_kind(condition_text, diagram_kind)
    if resolved_diagram_kind == "function_with_tangent":
        _, grid, trace = extract_graph_with_tangent(
            rgba,
            foreground_threshold=foreground_threshold,
            grid_mask_radius=grid_mask_radius,
            vertical_axis_x=vertical_axis_x,
            horizontal_axis_y=horizontal_axis_y,
            snap_tolerance_cells=snap_tolerance_cells,
            # Black tangent diagrams need a slightly wider centerline filter
            # than chromatic single-curve diagrams: after the straight line is
            # removed, the remaining raster stroke still alternates between
            # its upper and lower antialiased edges from one column to the next.
            smoothing_cells=max(smoothing_cells, 0.075),
            simplify_cells=max(simplify_cells, 0.050),
        )
    else:
        _, grid, trace = extract_graph(
            rgba,
            foreground_threshold=foreground_threshold,
            grid_mask_radius=grid_mask_radius,
            vertical_axis_x=vertical_axis_x,
            horizontal_axis_y=horizontal_axis_y,
            minimum_span_cells=minimum_span_cells,
            snap_tolerance_cells=snap_tolerance_cells,
            smoothing_cells=smoothing_cells,
            simplify_cells=simplify_cells,
            x_interval=resolved_x_interval,
        )
    resolved_graph_label = infer_graph_label(condition_text, graph_label)
    renderer = (
        render_graph_with_tangent_svg
        if resolved_diagram_kind == "function_with_tangent"
        else render_svg
    )
    render_pad_cells = (
        0 if resolved_diagram_kind == "function_with_tangent" else pad_cells
    )
    svg = renderer(
        grid,
        trace,
        cell_size=cell_size,
        pad_cells=render_pad_cells,
        path_mode=path_mode,
        bezier_error_cells=bezier_error_cells,
        endpoint_style=endpoint_style,
        include_labels=include_labels,
        curve_color=curve_color,
        graph_label=resolved_graph_label,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    asset_id = extract_id(source)
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
        save_debug_overlay(rgba, grid, trace, overlay_path)

    report_outputs(
        (svg_path, json_path, overlay_path),
        (grid, trace),
        (resolved_graph_label, resolved_diagram_kind, resolved_x_interval),
    )
    return svg_path, json_path, overlay_path
