"""Write the polygon converter's detailed geometry report."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass(frozen=True)
class PolygonDiagnostics:
    out: Path
    src: str
    dilation_results: dict[int, list[tuple[int, int]]] | None
    grayscale_source: bool
    w: int
    h: int
    base_mask: np.ndarray
    alpha_grid: dict[str, Any]
    alpha_info: dict[str, Any]
    pad_cells: int
    resolved_cell_size: float
    template_svg: Path | None
    integer_quad: list[tuple[int, int]]
    proto_info: dict[str, Any]
    source_polygon_points: list[tuple[int, int]]
    preprocessing_info: dict[str, int] | None = None


def write_polygon_diagnostics(report: PolygonDiagnostics) -> None:
    out = report.out
    src = report.src
    dilation_results = report.dilation_results
    grayscale_source = report.grayscale_source
    w = report.w
    h = report.h
    base_mask = report.base_mask
    alpha_grid = report.alpha_grid
    alpha_info = report.alpha_info
    pad_cells = report.pad_cells
    resolved_cell_size = report.resolved_cell_size
    template_svg = report.template_svg
    integer_quad = report.integer_quad
    proto_info = report.proto_info
    source_polygon_points = report.source_polygon_points
    with open(out.with_suffix(".txt"), "w", encoding="utf-8") as f:
        f.write(f"source={src}\n")
        if report.preprocessing_info is not None:
            f.write(
                f"fill_pixels_replaced={report.preprocessing_info['fill_pixels_replaced']}\n"
            )
            f.write(
                f"embedded_grid_pixels_replaced={report.preprocessing_info['embedded_grid_pixels_replaced']}\n"
            )
        if dilation_results is not None:
            f.write(f"dilation_coordinates={dilation_results}\n")
        if grayscale_source and dilation_results is not None:
            f.write(f"grayscale_dilation_coordinates={dilation_results}\n")
        f.write(f"size={w}x{h}\n")
        f.write(f"mask_pixels={int(base_mask.sum() // 255)}\n")
        f.write(f"grid_source={alpha_grid['source']}\n")
        f.write(f"grid_correction={alpha_grid.get('correction', 'none')}\n")
        f.write(f"alpha_shape_threshold={alpha_info['alpha_shape_threshold']}\n")
        f.write(f"alpha_shape_bbox={alpha_info['alpha_shape_bbox']}\n")
        f.write(f"alpha_grid_x_observed={alpha_grid['x']['observed']}\n")
        f.write(f"alpha_grid_y_observed={alpha_grid['y']['observed']}\n")
        f.write(f"alpha_grid_x_origin={alpha_grid['x']['origin']}\n")
        f.write(f"alpha_grid_y_origin={alpha_grid['y']['origin']}\n")
        f.write(f"alpha_grid_x_step={alpha_grid['x']['step']}\n")
        f.write(f"alpha_grid_y_step={alpha_grid['y']['step']}\n")
        f.write(f"alpha_grid_x_max_residual={alpha_grid['x']['max_residual']}\n")
        f.write(f"alpha_grid_y_max_residual={alpha_grid['y']['max_residual']}\n")
        f.write(f"alpha_grid_x_coverage={alpha_grid['x']['coverage']}\n")
        f.write(f"alpha_grid_y_coverage={alpha_grid['y']['coverage']}\n")
        f.write(f"pad_cells={pad_cells}\n")
        f.write(f"cell_size={resolved_cell_size}\n")
        f.write(f"template_svg={template_svg}\n")
        f.write(f"prototype_quad={integer_quad}\n")
        f.write(f"prototype_bbox={proto_info['bbox']}\n")
        f.write(f"source_quad_before_snap={proto_info['source_quad_before_snap']}\n")
        f.write(
            f"source_quad_on_alpha_grid={proto_info['source_quad_on_alpha_grid']}\n"
        )
        f.write(f"grid_indices={proto_info['grid_indices']}\n")
        f.write(f"source_polygon_points={source_polygon_points}\n")
        f.write(f"grid_bounds={proto_info['grid_bounds']}\n")
        f.write(f"svg_size={proto_info['svg_size']}\n")
