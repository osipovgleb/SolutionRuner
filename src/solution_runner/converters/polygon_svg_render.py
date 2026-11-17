"""Render a polygon and its coordinate grid into SVG."""

from pathlib import Path

import numpy as np

if __package__:
    from .polygon_grid_geometry import (
        _snap_quad_to_alpha_grid,
        _source_grid_coordinates,
    )
    from .polygon_image_masks import largest_component
    from .polygon_svg_template import (
        _extract_template_layers,
        _fmt_num,
        _replace_line_coords,
        _replace_points,
    )
else:
    from polygon_grid_geometry import _snap_quad_to_alpha_grid, _source_grid_coordinates
    from polygon_image_masks import largest_component
    from polygon_svg_template import (
        _extract_template_layers,
        _fmt_num,
        _replace_line_coords,
        _replace_points,
    )


def polygon_to_svg_path(poly: list[tuple[float, float]]) -> str:
    if not poly:
        return ""
    points = [*poly, poly[0]]
    d = [f"M{_fmt_num(points[0][0])},{_fmt_num(points[0][1])}"]
    for x, y in points[1:]:
        d.append(f"L{_fmt_num(x)},{_fmt_num(y)}")
    return " ".join(d)


def edge_segments_from_quad(poly: list[tuple[float, float]]) -> list[str]:
    if len(poly) < 3:
        return []
    out = []
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        out.append(f"M{_fmt_num(x1)},{_fmt_num(y1)} L{_fmt_num(x2)},{_fmt_num(y2)}")
    return out


def _svg_document(quad, template, geometry, style):
    columns, rows, svg_width, svg_height = geometry
    fill, padding, cell_size, keep_template_grid = style
    poly_path = polygon_to_svg_path(quad) + " Z"
    edge_paths = edge_segments_from_quad(quad)

    points_attr = " ".join([f"{_fmt_num(x)},{_fmt_num(y)}" for x, y in quad])

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {_fmt_num(svg_width)} {_fmt_num(svg_height)}" '
        f'width="{_fmt_num(svg_width)}" height="{_fmt_num(svg_height)}" '
        'shape-rendering="geometricPrecision" overflow="visible">\n'
    )

    if template and keep_template_grid:
        vertical = template.get("vertical_grid_line")
        horizontal = template.get("horizontal_grid_line")
        if vertical:
            for i in range(columns + 1):
                x = float(i) * float(cell_size)
                svg += f"  {_replace_line_coords(vertical, x, 0.0, x, svg_height)}\n"
        if horizontal:
            for i in range(rows + 1):
                y = float(i) * float(cell_size)
                svg += f"  {_replace_line_coords(horizontal, 0.0, y, svg_width, y)}\n"

    if template and template.get("fill_polygon"):
        svg += f"  {_replace_points(template['fill_polygon'], points_attr)}\n"
    else:
        svg += (
            f'<g id="prototype-fill" fill="{fill}" stroke="none">\n'
            f'  <path d="{poly_path}"/>\n'
            "</g>\n"
        )

    if template and template.get("outline_polygon"):
        svg += f"  {_replace_points(template['outline_polygon'], points_attr)}\n"
    else:
        svg += (
            '<g id="prototype-sections" fill="none" stroke="#000" stroke-width="1">\n'
        )
        for i, p in enumerate(edge_paths):
            svg += f'  <path id="edge-{i}" d="{p}"/>\n'
        svg += "  </g>\n"

    scale_x1 = float(padding) * float(cell_size)
    scale_x2 = scale_x1 + float(cell_size)
    scale_y = svg_height - float(cell_size)
    scale_text_y = scale_y + float(cell_size) * 0.62
    scale_font_size = max(7.0, float(cell_size) * 0.5)
    scale_stroke_width = max(1.5, float(cell_size) * 0.09)
    svg += '<g id="scale-label" fill="#0D0F0F">\n'
    svg += (
        f'  <line x1="{_fmt_num(scale_x1)}" y1="{_fmt_num(scale_y)}" '
        f'x2="{_fmt_num(scale_x2)}" y2="{_fmt_num(scale_y)}" '
        f'stroke="#0D0F0F" stroke-width="{_fmt_num(scale_stroke_width)}"/>\n'
    )
    svg += (
        f'  <text x="{_fmt_num((scale_x1 + scale_x2) / 2.0)}" '
        f'y="{_fmt_num(scale_text_y)}" text-anchor="middle" '
        f'font-family="sans-serif" font-size="{_fmt_num(scale_font_size)}">'
        "1 &#1089;&#1084;</text>\n"
    )
    svg += "</g>\n"

    svg += "</svg>\n"
    return svg


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
    *,
    quad_from_mask,
) -> tuple[list[tuple[float, float]], dict]:
    comp = largest_component(mask)
    if comp.sum() == 0:
        raise ValueError("no_contours")

    ys, xs = np.where(comp > 0)

    source_quad = quad_from_mask(
        comp,
        pad_cells=0,
        cell_size=1.0,
        width=width,
        height=height,
        expected_vertices=expected_vertices,
    )
    if len(source_quad) not in {3, 4}:
        raise ValueError("no_contours")

    if alpha_grid is None:
        raise ValueError("alpha_grid_required")
    snapped_source_quad, grid_indices = _snap_quad_to_alpha_grid(
        source_quad, alpha_grid
    )
    source_grid_points = _source_grid_coordinates(grid_indices, alpha_grid)

    template = _extract_template_layers(template_svg)
    if template is None:
        raise ValueError("template_svg_required")

    padding = max(0, pad_cells)
    min_source_x = min(x for x, _ in source_grid_points)
    max_source_x = max(x for x, _ in source_grid_points)
    min_source_y = min(y for _, y in source_grid_points)
    max_source_y = max(y for _, y in source_grid_points)
    min_canvas_x = min_source_x - padding
    max_canvas_x = max_source_x + padding
    min_canvas_y = min_source_y - padding
    max_canvas_y = max_source_y + padding
    columns = max_canvas_x - min_canvas_x
    rows = max_canvas_y - min_canvas_y
    svg_width = float(columns) * float(cell_size)
    svg_height = float(rows) * float(cell_size)
    quad = [
        (
            float(x - min_canvas_x) * float(cell_size),
            float(max_canvas_y - y) * float(cell_size),
        )
        for x, y in source_grid_points
    ]

    svg = _svg_document(
        quad,
        template,
        (columns, rows, svg_width, svg_height),
        (fill, padding, cell_size, keep_template_grid),
    )
    out_path.write_text(svg, encoding="utf-8")

    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    return quad, {
        "bbox": (min(xs), min(ys), max(xs), max(ys)),
        "source_quad_before_snap": source_quad,
        "source_quad_on_alpha_grid": snapped_source_quad,
        "grid_indices": grid_indices,
        "source_grid_points": source_grid_points,
        "grid_bounds": (min_canvas_x, min_canvas_y, max_canvas_x, max_canvas_y),
        "svg_size": (svg_width, svg_height),
    }
