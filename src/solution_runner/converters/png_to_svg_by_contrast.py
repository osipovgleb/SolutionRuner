#!/usr/bin/env python3
import sys
from pathlib import Path
from typing import TextIO

import cv2
import numpy as np

if __package__:
    from . import (
        polygon_cli,
        polygon_contours,
        polygon_diagnostics,
        polygon_grid_axis,
        polygon_grid_geometry,
        polygon_grid_lattice,
        polygon_image_description,
        polygon_image_io,
        polygon_image_masks,
        polygon_svg_render,
        polygon_svg_template,
    )
else:
    import polygon_cli
    import polygon_contours
    import polygon_diagnostics
    import polygon_grid_axis
    import polygon_grid_geometry
    import polygon_grid_lattice
    import polygon_image_description
    import polygon_image_io
    import polygon_image_masks
    import polygon_svg_render
    import polygon_svg_template


is_url = polygon_image_io.is_url
load_image = polygon_image_io.load_image
extract_id = polygon_image_io.extract_id
contrast_mask = polygon_image_masks.contrast_mask
infer_cell_size_from_svg = polygon_image_masks.infer_cell_size_from_svg
largest_component = polygon_image_masks.largest_component
_stable_ordered_contour_polygon = polygon_contours._stable_ordered_contour_polygon
quad_from_mask = polygon_contours.quad_from_mask
alpha_shape_mask = polygon_image_masks.alpha_shape_mask
is_grayscale_source = polygon_image_masks.is_grayscale_source
grayscale_shape_mask = polygon_image_masks.grayscale_shape_mask
opaque_color_shape_mask = polygon_image_masks.opaque_color_shape_mask
_projection_bands = polygon_grid_axis._projection_bands
_fit_grid_axis = polygon_grid_axis._fit_grid_axis
_square_step_candidates = polygon_grid_axis._square_step_candidates
_fit_axis_at_step = polygon_grid_lattice._fit_axis_at_step
_refine_shared_step = polygon_grid_lattice._refine_shared_step
_fit_square_lattice = polygon_grid_lattice._fit_square_lattice
_promote_clean_grid_fundamental = polygon_grid_lattice._promote_clean_grid_fundamental
infer_grid_from_alpha = polygon_grid_geometry.infer_grid_from_alpha
infer_grid_from_grayscale = polygon_grid_geometry.infer_grid_from_grayscale
infer_grid_from_opaque_color = polygon_grid_geometry.infer_grid_from_opaque_color
_snap_quad_to_alpha_grid = polygon_grid_geometry._snap_quad_to_alpha_grid


def _select_grid_for_quad(quad: list[tuple[float, float]], grids: list[dict]) -> dict:
    """Choose a grid after validating that polygon vertices exist."""
    if not quad:
        raise ValueError("polygon_vertices_not_found")
    return polygon_grid_geometry._select_grid_for_quad(quad, grids)


_measure_axis_step = polygon_grid_geometry._measure_axis_step
_source_grid_coordinates = polygon_grid_geometry._source_grid_coordinates


def _require_stable_grayscale_dilation_coordinates(
    mask: np.ndarray,
    grid: dict,
    width: int,
    height: int,
    expected_vertices: int | None,
    radii: tuple[int, ...] = (0, 1, 2, 3, 4),
) -> dict[int, list[tuple[int, int]]]:
    """Reject selected geometry unless every dilation radius snaps identically."""

    results: dict[int, list[tuple[int, int]]] = {}
    signatures: set[tuple[tuple[int, int], ...]] = set()
    for radius in radii:
        if radius == 0:
            expanded = mask
        else:
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (radius * 2 + 1, radius * 2 + 1),
            )
            expanded = cv2.dilate(mask, kernel)

        polygon = quad_from_mask(
            expanded,
            pad_cells=0,
            cell_size=1.0,
            width=width,
            height=height,
            expected_vertices=expected_vertices,
        )
        if len(polygon) not in {3, 4}:
            raise ValueError(
                "grayscale_dilation_consensus_unavailable: "
                f"radius={radius} did not produce a polygon; будь осторожнее"
            )

        _, grid_indices = _snap_quad_to_alpha_grid(polygon, grid)
        coordinates = sorted(
            _source_grid_coordinates(grid_indices, grid),
            key=lambda point: (point[1], point[0]),
        )
        results[radius] = coordinates
        signatures.add(tuple(coordinates))

    if len(signatures) != 1:
        variants = "; ".join(
            f"radius_{radius}={coordinates}" for radius, coordinates in results.items()
        )
        raise ValueError(
            "grayscale_dilation_consensus_unstable: coordinates change after "
            f"dilation ({variants}); будь осторожнее"
        )
    return results


_fmt_num = polygon_svg_template._fmt_num
_parse_points = polygon_svg_template._parse_points
_poly_area_abs = polygon_svg_template._poly_area_abs
_replace_points = polygon_svg_template._replace_points
_scale_line_coords = polygon_svg_template._scale_line_coords
_replace_line_coords = polygon_svg_template._replace_line_coords
_parse_attr_float = polygon_svg_template._parse_attr_float
_collect_grid_from_lines = polygon_svg_template._collect_grid_from_lines
_snap_to_grid_points_by_side = polygon_svg_template._snap_to_grid_points_by_side
_infer_grid_from_gray = polygon_svg_template._infer_grid_from_gray
_extract_template_layers = polygon_svg_template._extract_template_layers
polygon_to_svg_path = polygon_svg_render.polygon_to_svg_path
edge_segments_from_quad = polygon_svg_render.edge_segments_from_quad


def svg_for_mask(
    mask: np.ndarray,
    out_path: Path,
    width: int,
    height: int,
    fill: str = "black",
    pad_cells: int = 2,
    cell_size: float = 1.0,
    template_svg: Path | None = None,
    keep_template_grid: bool = False,
    gray: np.ndarray | None = None,
    auto_grid: bool = False,
    alpha_grid: dict | None = None,
    expected_vertices: int | None = None,
) -> tuple[list[tuple[float, float]], dict]:
    return polygon_svg_render.svg_for_mask(
        mask=mask,
        out_path=out_path,
        width=width,
        height=height,
        fill=fill,
        pad_cells=pad_cells,
        cell_size=cell_size,
        template_svg=template_svg,
        keep_template_grid=keep_template_grid,
        gray=gray,
        auto_grid=auto_grid,
        alpha_grid=alpha_grid,
        expected_vertices=expected_vertices,
        quad_from_mask=quad_from_mask,
    )


def _detect_shape_and_grid(rgba, dimensions, expected_vertices):
    w, h = dimensions
    alpha = rgba[:, :, 3]
    grayscale_source = is_grayscale_source(rgba)
    if grayscale_source:
        base_mask, alpha_info = grayscale_shape_mask(rgba)
        alpha_grid = infer_grid_from_grayscale(rgba)
        alpha_grid["coordinate_anchor"] = "canvas"
        alpha_grid["source_height"] = h
    elif not bool(np.any(alpha < 250)):
        base_mask, alpha_info = opaque_color_shape_mask(rgba)
        alpha_grid = infer_grid_from_opaque_color(rgba)
    else:
        base_mask, alpha_info = alpha_shape_mask(rgba)
        grid_candidates = []
        alpha_grid_error: ValueError | None = None
        try:
            grid_candidates.append(
                infer_grid_from_alpha(rgba, alpha_info["alpha_shape_threshold"])
            )
        except ValueError as error:
            alpha_grid_error = error
        try:
            grid_candidates.append(infer_grid_from_grayscale(rgba))
        except ValueError:
            if not grid_candidates and alpha_grid_error is not None:
                raise alpha_grid_error

        component = largest_component(base_mask)
        source_quad = quad_from_mask(
            component,
            pad_cells=0,
            cell_size=1.0,
            width=w,
            height=h,
            expected_vertices=expected_vertices,
        )
        alpha_grid = _select_grid_for_quad(source_quad, grid_candidates)
        if alpha_grid.get("source") == "grayscale":
            alpha_grid["coordinate_anchor"] = "canvas"
            alpha_grid["source_height"] = h

    return base_mask, alpha_info, alpha_grid, grayscale_source


_source_format = polygon_image_description._source_format
_visual_type = polygon_image_description._visual_type


def run(
    src: str,
    out_dir: Path,
    pad_cells: int,
    quantile: float,
    min_area: int,
    close_px: int,
    simplify: float,
    keep_template_grid: bool,
    cell_size: float | None,
    template_svg: Path | None,
    auto_grid: bool,
    expected_vertices: int | None = None,
    output_stream: TextIO | None = None,
) -> Path:
    rgba, source_info = load_image(src)
    gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)

    image_format = _source_format(src, source_info)

    h, w = gray.shape
    dilation_results: dict[int, list[tuple[int, int]]] | None = None
    base_mask, alpha_info, alpha_grid, grayscale_source = _detect_shape_and_grid(
        rgba, (w, h), expected_vertices
    )

    if grayscale_source or expected_vertices == 3:
        dilation_results = _require_stable_grayscale_dilation_coordinates(
            base_mask,
            alpha_grid,
            w,
            h,
            expected_vertices,
        )

    visual_type = _visual_type(rgba, base_mask)

    resolved_cell_size = 1.0 if cell_size is None else float(round(cell_size))
    if template_svg is not None and cell_size is None:
        detected = infer_cell_size_from_svg(template_svg)
        if detected > 0:
            resolved_cell_size = float(round(detected))

    filename = Path(f"{extract_id(src)}.svg")
    out = out_dir / filename
    out_dir.mkdir(parents=True, exist_ok=True)
    if base_mask.sum() == 0:
        raise ValueError("empty_mask")

    quad, proto_info = svg_for_mask(
        base_mask,
        out,
        w,
        h,
        fill="blue",
        pad_cells=pad_cells,
        cell_size=resolved_cell_size,
        template_svg=template_svg,
        keep_template_grid=keep_template_grid,
        gray=gray,
        auto_grid=auto_grid,
        alpha_grid=alpha_grid,
        expected_vertices=expected_vertices,
    )

    integer_quad = [(round(x), round(y)) for x, y in quad]
    source_polygon_points = sorted(
        proto_info["source_grid_points"],
        key=lambda point: (point[1], point[0]),
    )
    detected_x_step = _measure_axis_step(alpha_grid["x"])
    detected_y_step = _measure_axis_step(alpha_grid["y"])
    stream = output_stream or sys.stdout
    print(f"polygon_points={source_polygon_points}", file=stream)
    print(f"svg_polygon_points={integer_quad}", file=stream)
    print(f"image_format={image_format}", file=stream)
    print(f"visual_type={visual_type}", file=stream)
    print(f"grid_step_x={_fmt_num(detected_x_step)}", file=stream)
    print(f"grid_step_y={_fmt_num(detected_y_step)}", file=stream)
    print(f"grid_step_shared={_fmt_num(float(alpha_grid['cell']))}", file=stream)

    polygon_diagnostics.write_polygon_diagnostics(
        polygon_diagnostics.PolygonDiagnostics(
            out=out,
            src=src,
            dilation_results=dilation_results,
            grayscale_source=grayscale_source,
            w=w,
            h=h,
            base_mask=base_mask,
            alpha_grid=alpha_grid,
            alpha_info=alpha_info,
            pad_cells=pad_cells,
            resolved_cell_size=resolved_cell_size,
            template_svg=template_svg,
            integer_quad=integer_quad,
            proto_info=proto_info,
            source_polygon_points=source_polygon_points,
        )
    )

    return out


def main():
    return polygon_cli.polygon_main(run)


if __name__ == "__main__":
    main()
