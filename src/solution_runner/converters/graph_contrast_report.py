"""Write the graph converter's user-facing output summary."""

from __future__ import annotations

import sys

from .graph_contrast_paths import _fmt


def report_outputs(artifacts, geometry, diagram):
    """Report written artifacts and recovered graph geometry on stdout."""
    svg_path, json_path, overlay_path = artifacts
    grid, trace = geometry
    graph_label, diagram_kind, x_interval = diagram
    lines = [f"svg={svg_path}", f"diagnostics={json_path}"]
    if overlay_path is not None:
        lines.append(f"debug_overlay={overlay_path}")
    lines.extend(
        [
            f"grid_step=({_fmt(grid.vertical.step, 4)}, {_fmt(grid.horizontal.step, 4)})",
            (
                "axes="
                f"(vertical_x={_fmt(grid.vertical_axis_x, 3)}, "
                f"horizontal_y={_fmt(grid.horizontal_axis_y, 3)})"
            ),
            (
                "curve_endpoints="
                f"[({_fmt(trace.start.logical_x, 3)}, {_fmt(trace.start.logical_y, 3)}), "
                f"({_fmt(trace.end.logical_x, 3)}, {_fmt(trace.end.logical_y, 3)})]"
            ),
            f"graph_label={graph_label}",
            f"diagram_kind={diagram_kind}",
        ]
    )
    if trace.tangent is not None:
        lines.append(f"tangent_slope={_fmt(trace.tangent.logical_slope, 6)}")
    if x_interval is not None and diagram_kind == "single_curve":
        lines.append(
            "condition_x_interval="
            f"({_fmt(x_interval.left, 3)}, {_fmt(x_interval.right, 3)})"
        )
    sys.stdout.write("\n".join(lines) + "\n")
