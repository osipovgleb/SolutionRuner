"""Detect circular rings and render their SVG geometry."""

import logging
from pathlib import Path
from urllib.parse import urlparse

import cv2
import numpy as np

if __package__:
    from .polygon_grid_geometry import (
        _measure_axis_step,
        infer_grid_from_alpha,
        infer_grid_from_grayscale,
        infer_grid_from_opaque_color,
    )
    from .polygon_image_masks import alpha_shape_mask, largest_component
    from .polygon_svg_template import _fmt_num
else:
    from polygon_grid_geometry import (
        _measure_axis_step,
        infer_grid_from_alpha,
        infer_grid_from_grayscale,
        infer_grid_from_opaque_color,
    )
    from polygon_image_masks import alpha_shape_mask, largest_component
    from polygon_svg_template import _fmt_num


def _ring_mask(rgba: np.ndarray) -> tuple[np.ndarray, str]:
    rgb = rgba[:, :, :3].astype(np.int16)
    alpha = rgba[:, :, 3]
    blue_mask = (
        (rgb[:, :, 2] - rgb[:, :, 0] >= 25)
        & (rgb[:, :, 2] - rgb[:, :, 1] >= 8)
        & (alpha >= 80)
    ).astype(np.uint8) * 255
    blue_mask = cv2.morphologyEx(
        blue_mask,
        cv2.MORPH_CLOSE,
        np.ones((3, 3), dtype=np.uint8),
    )
    blue_component = largest_component(blue_mask)
    if int(np.count_nonzero(blue_component)) >= 500:
        return blue_component, "blue"

    alpha_mask = (alpha >= 128).astype(np.uint8) * 255
    alpha_mask = cv2.morphologyEx(
        alpha_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    )
    alpha_component = largest_component(alpha_mask)
    if int(np.count_nonzero(alpha_component)) < 500:
        raise ValueError("ring_not_found")
    return alpha_component, "grayscale"


def _fit_circle_to_contour(contour: np.ndarray) -> tuple[float, float, float]:
    points = contour[:, 0, :].astype(np.float64)
    x = points[:, 0]
    y = points[:, 1]
    matrix = np.column_stack((2.0 * x, 2.0 * y, np.ones_like(x)))
    target = x * x + y * y
    cx, cy, constant = np.linalg.lstsq(matrix, target, rcond=None)[0]
    radius_squared = constant + cx * cx + cy * cy
    if radius_squared <= 0:
        raise ValueError("invalid_circle_radius")
    return float(cx), float(cy), float(np.sqrt(radius_squared))


def _fit_ring_circles(
    mask: np.ndarray,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
]:
    contours, hierarchy = cv2.findContours(
        mask.copy(),
        cv2.RETR_CCOMP,
        cv2.CHAIN_APPROX_NONE,
    )
    if hierarchy is None:
        raise ValueError("ring_contours_not_found")

    nodes = hierarchy[0]
    outer_index = max(
        (index for index, node in enumerate(nodes) if int(node[3]) == -1),
        key=lambda index: abs(cv2.contourArea(contours[index])),
    )
    inner_indices = [
        index for index, node in enumerate(nodes) if int(node[3]) == outer_index
    ]
    if not inner_indices:
        raise ValueError("ring_hole_not_found")
    inner_index = max(
        inner_indices,
        key=lambda index: abs(cv2.contourArea(contours[index])),
    )

    outer_circle = _fit_circle_to_contour(contours[outer_index])
    inner_circle = _fit_circle_to_contour(contours[inner_index])
    if inner_circle[2] >= outer_circle[2]:
        raise ValueError("invalid_ring_radii")
    return outer_circle, inner_circle


def _nearest_lattice_radius_squared(radius_cells: float) -> int:
    target = radius_cells * radius_cells
    limit = max(2, int(np.ceil(radius_cells)) + 2)
    representable = {
        dx * dx + dy * dy
        for dx in range(-limit, limit + 1)
        for dy in range(-limit, limit + 1)
        if dx != 0 or dy != 0
    }
    return min(
        representable,
        key=lambda value: (abs(float(value) - target), value),
    )


def _integer_circle_points(
    center: tuple[int, int],
    radius_squared: int,
) -> list[tuple[int, int]]:
    cx, cy = center
    limit = int(np.ceil(np.sqrt(float(radius_squared))))
    points = [
        (cx + dx, cy + dy)
        for dx in range(-limit, limit + 1)
        for dy in range(-limit, limit + 1)
        if dx * dx + dy * dy == radius_squared
    ]
    if not points:
        raise ValueError("integer_circle_points_not_found")
    return sorted(points, key=lambda point: (point[1], point[0]))


def _ring_grid_candidate(
    rgba: np.ndarray,
    outer_circle: tuple[float, float, float],
    inner_circle: tuple[float, float, float],
) -> tuple[dict, float, float, float]:
    alpha = rgba[:, :, 3]
    candidates: list[dict] = []
    try:
        candidates.append(infer_grid_from_grayscale(rgba))
    except ValueError:
        logging.getLogger(__name__).debug("Grayscale grid unavailable for ring")

    if bool(np.any(alpha < 250)):
        try:
            _, alpha_info = alpha_shape_mask(rgba)
            candidates.append(
                infer_grid_from_alpha(
                    rgba,
                    int(alpha_info["alpha_shape_threshold"]),
                )
            )
        except ValueError:
            logging.getLogger(__name__).debug("Alpha grid unavailable for ring")
    else:
        try:
            candidates.append(infer_grid_from_opaque_color(rgba))
        except ValueError:
            logging.getLogger(__name__).debug("Opaque-color grid unavailable for ring")

    if not candidates:
        raise ValueError("ring_grid_not_found")

    height = rgba.shape[0]
    outer_cx, outer_cy, outer_radius = outer_circle
    inner_cx, inner_cy, inner_radius = inner_circle
    circle_cx = (outer_cx + inner_cx) / 2.0
    circle_cy = (outer_cy + inner_cy) / 2.0
    scored: list[tuple[float, dict, float, float, float]] = []

    for grid in candidates:
        step_x = _measure_axis_step(grid["x"])
        step_y = _measure_axis_step(grid["y"])
        measured_cell = (step_x + step_y) / 2.0
        disagreement = abs(step_x - step_y) / measured_cell
        center_x_cells = circle_cx / measured_cell
        center_y_cells = (height - circle_cy) / measured_cell
        center_error = float(
            np.hypot(
                center_x_cells - round(center_x_cells),
                center_y_cells - round(center_y_cells),
            )
        )
        outer_raw_squared = (outer_radius / measured_cell) ** 2
        inner_raw_squared = (inner_radius / measured_cell) ** 2
        radius_error = abs(
            outer_raw_squared
            - _nearest_lattice_radius_squared(outer_radius / measured_cell)
        ) + abs(
            inner_raw_squared
            - _nearest_lattice_radius_squared(inner_radius / measured_cell)
        )
        score = (
            float(grid.get("confidence", 0.0))
            - 2.0 * disagreement
            - 0.25 * center_error
            - 0.03 * radius_error
        )
        scored.append((score, grid, step_x, step_y, measured_cell))

    _, grid, step_x, step_y, measured_cell = max(
        scored,
        key=lambda item: item[0],
    )
    return grid, step_x, step_y, measured_cell


def _circle_path(cx: float, cy: float, radius: float) -> str:
    return (
        f"M {_fmt_num(cx + radius)} {_fmt_num(cy)} "
        f"A {_fmt_num(radius)} {_fmt_num(radius)} 0 1 0 "
        f"{_fmt_num(cx - radius)} {_fmt_num(cy)} "
        f"A {_fmt_num(radius)} {_fmt_num(radius)} 0 1 0 "
        f"{_fmt_num(cx + radius)} {_fmt_num(cy)} Z"
    )


def _ring_svg(
    out_path: Path,
    center: tuple[int, int],
    outer_radius_squared: int,
    inner_radius_squared: int,
    outer_points: list[tuple[int, int]],
    pad_cells: int,
    cell_size: float,
    include_grid: bool,
    include_scale: bool,
) -> tuple[int, int, int, int]:
    padding = max(0, pad_cells)
    radius_extent = int(np.ceil(np.sqrt(float(outer_radius_squared))))
    min_canvas_x = center[0] - radius_extent - padding
    max_canvas_x = center[0] + radius_extent + padding
    min_canvas_y = center[1] - radius_extent - padding - (1 if include_scale else 0)
    max_canvas_y = center[1] + radius_extent + padding
    columns = max_canvas_x - min_canvas_x
    rows = max_canvas_y - min_canvas_y
    svg_width = float(columns) * cell_size
    svg_height = float(rows) * cell_size
    svg_cx = float(center[0] - min_canvas_x) * cell_size
    svg_cy = float(max_canvas_y - center[1]) * cell_size
    outer_radius = float(np.sqrt(float(outer_radius_squared))) * cell_size
    inner_radius = float(np.sqrt(float(inner_radius_squared))) * cell_size
    outer_path = _circle_path(svg_cx, svg_cy, outer_radius)
    inner_path = _circle_path(svg_cx, svg_cy, inner_radius)

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {_fmt_num(svg_width)} {_fmt_num(svg_height)}" '
        f'width="{_fmt_num(svg_width)}" height="{_fmt_num(svg_height)}" '
        'shape-rendering="geometricPrecision">\n'
    )
    if include_grid:
        svg += '  <g id="grid" fill="none" stroke="#C0BFBF" stroke-width="0.5">\n'
        for column in range(columns + 1):
            x = float(column) * cell_size
            svg += (
                f'    <line x1="{_fmt_num(x)}" y1="0" '
                f'x2="{_fmt_num(x)}" y2="{_fmt_num(svg_height)}"/>\n'
            )
        for row in range(rows + 1):
            y = float(row) * cell_size
            svg += (
                f'    <line x1="0" y1="{_fmt_num(y)}" '
                f'x2="{_fmt_num(svg_width)}" y2="{_fmt_num(y)}"/>\n'
            )
        svg += "  </g>\n"

    svg += (
        f'  <path id="ring-fill" d="{outer_path} {inner_path}" '
        'fill="#143B8F" fill-opacity="0.5" fill-rule="evenodd"/>\n'
    )
    svg += '  <g id="ring-outline" fill="none" stroke="#143B8F" stroke-width="1">\n'
    svg += (
        f'    <circle cx="{_fmt_num(svg_cx)}" cy="{_fmt_num(svg_cy)}" '
        f'r="{_fmt_num(outer_radius)}"/>\n'
    )
    svg += (
        f'    <circle cx="{_fmt_num(svg_cx)}" cy="{_fmt_num(svg_cy)}" '
        f'r="{_fmt_num(inner_radius)}"/>\n'
    )
    svg += "  </g>\n"

    if include_scale:
        scale_x1 = float(padding) * cell_size
        scale_x2 = scale_x1 + cell_size
        scale_y = svg_height - cell_size
        scale_text_y = scale_y + cell_size * 0.62
        scale_font_size = max(7.0, cell_size * 0.5)
        scale_stroke_width = max(1.5, cell_size * 0.09)
        svg += '  <g id="scale-label" fill="#0D0F0F">\n'
        svg += (
            f'    <line x1="{_fmt_num(scale_x1)}" y1="{_fmt_num(scale_y)}" '
            f'x2="{_fmt_num(scale_x2)}" y2="{_fmt_num(scale_y)}" '
            f'stroke="#0D0F0F" stroke-width="{_fmt_num(scale_stroke_width)}"/>\n'
        )
        svg += (
            f'    <text x="{_fmt_num((scale_x1 + scale_x2) / 2.0)}" '
            f'y="{_fmt_num(scale_text_y)}" text-anchor="middle" '
            f'font-family="sans-serif" font-size="{_fmt_num(scale_font_size)}">'
            "1 &#1089;&#1084;</text>\n"
        )
        svg += "  </g>\n"

    svg += "</svg>\n"
    out_path.write_text(svg, encoding="utf-8")
    return min_canvas_x, min_canvas_y, max_canvas_x, max_canvas_y


def _image_format(source_info: str, src: str) -> str:
    source_info_text = str(source_info)
    if source_info_text.lower().startswith("image/"):
        raw_format = source_info_text.split("/", 1)[1].split(";", 1)[0]
    else:
        raw_format = Path(source_info_text).suffix.lstrip(".")
        if not raw_format:
            raw_format = Path(urlparse(src).path).suffix.lstrip(".")
    raw_format_lower = raw_format.lower()
    if "bmp" in raw_format_lower:
        return "BMP"
    if raw_format_lower in {"jpg", "jpeg", "pjpeg"}:
        return "JPEG"
    return raw_format_lower.upper() if raw_format_lower else "UNKNOWN"
