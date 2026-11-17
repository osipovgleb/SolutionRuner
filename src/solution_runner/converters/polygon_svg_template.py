"""Read and adapt SVG template grids and polygon layers."""

import re
from pathlib import Path

import cv2
import numpy as np


def _fmt_num(v: float) -> str:
    if abs(v - round(v)) < 1e-6:
        return str(round(v))
    return f"{v:.3f}".rstrip("0").rstrip(".")


def _parse_points(points_value: str) -> list[tuple[float, float]]:
    nums = re.findall(r"-?\d+(?:\.\d+)?", points_value)
    pts: list[tuple[float, float]] = []
    if len(nums) < 6:
        return pts
    for a, b in zip(nums[0::2], nums[1::2]):
        pts.append((float(a), float(b)))
    return pts


def _poly_area_abs(poly: list[tuple[float, float]]) -> float:
    if len(poly) < 3:
        return 0.0
    area = 0.0
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        area += x1 * y2 - x2 * y1
    return abs(area) * 0.5


def _replace_points(node: str, points_text: str) -> str:
    return re.sub(
        r'points\s*=\s*["\'][^"\']*["\']',
        f'points="{points_text}"',
        node,
        count=1,
    )


def _scale_line_coords(node: str, sx: float, sy: float) -> str:
    def _replace_attr(text: str, old_key: str, scale: float) -> str:
        return re.sub(
            rf'{old_key}\s*=\s*["\']([0-9.\-]+)["\']',
            lambda m: f'{old_key}="{_fmt_num(float(m.group(1)) * scale)}"',
            text,
            flags=re.IGNORECASE,
        )

    out = _replace_attr(node, "x1", sx)
    out = _replace_attr(out, "x2", sx)
    out = _replace_attr(out, "y1", sy)
    out = _replace_attr(out, "y2", sy)
    return out


def _replace_line_coords(node: str, x1: float, y1: float, x2: float, y2: float) -> str:
    values = {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
    out = node
    for key, value in values.items():
        out = re.sub(
            rf'{key}\s*=\s*["\'][0-9.\-]+["\']',
            f'{key}="{_fmt_num(value)}"',
            out,
            count=1,
            flags=re.IGNORECASE,
        )
    return out


def _parse_attr_float(node: str, key: str) -> float | None:
    m = re.search(rf'{key}\s*=\s*["\']([0-9.\-]+)["\']', node, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _collect_grid_from_lines(line_nodes: list[str]) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for node in line_nodes:
        x1 = _parse_attr_float(node, "x1")
        x2 = _parse_attr_float(node, "x2")
        y1 = _parse_attr_float(node, "y1")
        y2 = _parse_attr_float(node, "y2")
        if x1 is None or x2 is None or y1 is None or y2 is None:
            continue
        if abs(x2 - x1) <= 1.0 and abs(y2 - y1) > 1.0:
            xs.extend([x1, x2])
        if abs(y2 - y1) <= 1.0 and abs(x2 - x1) > 1.0:
            ys.extend([y1, y2])

    def _dedup(vals: list[float], eps: float = 0.75) -> list[float]:
        if not vals:
            return []
        vals = sorted({round(v, 4) for v in vals})
        out = [vals[0]]
        for v in vals[1:]:
            if abs(v - out[-1]) >= eps:
                out.append(v)
        return out

    return _dedup(xs), _dedup(ys)


def _snap_to_grid_points_by_side(
    quad: list[tuple[float, float]],
    grid_x: list[float],
    grid_y: list[float],
) -> list[tuple[float, float]]:
    if not quad:
        return []
    if not grid_x and not grid_y:
        return quad

    xs = [p[0] for p in quad]
    ys = [p[1] for p in quad]
    if grid_x:
        left_x = min(grid_x, key=lambda x: abs(x - min(xs)))
        right_x = min(grid_x, key=lambda x: abs(x - max(xs)))
        sx = sorted({round(x, 4) for x in grid_x})
        # force pair for symmetry in rare cases
        if abs(left_x - right_x) < 1e-6 and len(sx) >= 2:
            right_x = sx[1] if sx[0] == left_x else sx[0]

    if grid_y:
        top_y = min(grid_y, key=lambda y: abs(y - min(ys)))
        bot_y = min(grid_y, key=lambda y: abs(y - max(ys)))
        sy = sorted({round(y, 4) for y in grid_y})
        if abs(top_y - bot_y) < 1e-6 and len(sy) >= 2:
            bot_y = sy[1] if sy[0] == top_y else sy[0]

    idx_by_y = sorted(range(4), key=lambda i: ys[i])
    top_set = set(idx_by_y[:2])

    idx_by_x = sorted(range(4), key=lambda i: xs[i])
    left_set = set(idx_by_x[:2])

    out = []
    for i, (x, y) in enumerate(quad):
        out_x = x
        out_y = y
        if grid_x:
            out_x = left_x if i in left_set else right_x
        if grid_y:
            out_y = top_y if i in top_set else bot_y
        out.append((out_x, out_y))

    return out


def _infer_grid_from_gray(
    gray: np.ndarray, comp_bbox: tuple[float, float, float, float] | None = None
) -> tuple[list[float], list[float]]:
    h, w = gray.shape
    if h < 20 or w < 20:
        return [], []

    proc = cv2.GaussianBlur(gray, (3, 3), 0)
    edges = cv2.Canny(proc, 45, 140)

    if comp_bbox is not None:
        x0, y0, x1, y1 = comp_bbox
        x0 = max(0, int(x0) - 40)
        x1 = min(w, int(x1) + 41)
        y0 = max(0, int(y0) - 40)
        y1 = min(h, int(y1) + 41)
        roi = np.zeros_like(edges)
        roi[y0:y1, x0:x1] = 255
        edges = cv2.bitwise_and(edges, roi)

    min_len = max(24, int(min(w, h) * 0.12))
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=max(20, min_len // 2),
        minLineLength=min_len,
        maxLineGap=8,
    )
    if lines is None:
        return [], []

    xs: list[float] = []
    ys: list[float] = []
    for l in lines.reshape(-1, 4):
        x1, y1, x2, y2 = map(float, l)
        dx = x2 - x1
        dy = y2 - y1
        ll = (dx * dx + dy * dy) ** 0.5
        if ll < float(min_len):
            continue
        angle = abs(np.degrees(np.arctan2(dy, dx)))
        if angle > 85.0 and angle < 95.0:
            xs.extend([x1, x2])
        elif angle < 5.0 or angle > 175.0:
            ys.extend([y1, y2])

    def _dedup(vals: list[float], eps: float = 3.0) -> list[float]:
        if not vals:
            return []
        vals = sorted({round(v, 3) for v in vals})
        out = [vals[0]]
        for v in vals[1:]:
            if abs(v - out[-1]) >= eps:
                out.append(v)
        return out

    return _dedup(xs), _dedup(ys)


def _select_template_polygons(polygon_nodes, dimensions):
    vb_w, vb_h = dimensions
    fill_polygons = []
    for node in polygon_nodes:
        fill = re.search(r'fill\s*=\s*["\']([^"\']+)["\']', node, flags=re.IGNORECASE)
        if not fill or fill.group(1).strip().lower() == "none":
            continue
        pts = re.search(r'points\s*=\s*["\']([^"\']*)["\']', node, flags=re.IGNORECASE)
        if not pts:
            continue
        points = _parse_points(pts.group(1))
        if len(points) < 3:
            continue
        area = _poly_area_abs(points)
        minx = min(p[0] for p in points)
        maxx = max(p[0] for p in points)
        miny = min(p[1] for p in points)
        maxy = max(p[1] for p in points)
        in_box = False
        if vb_w and vb_h:
            in_box = (
                minx >= -1e-6
                and maxx <= vb_w + 1e-6
                and miny >= -1e-6
                and maxy <= vb_h + 1e-6
            )
        fill_polygons.append((area, in_box, node))

    fill_polygon = None
    bbox_fill = [p for p in fill_polygons if p[1]]
    if bbox_fill:
        fill_polygon = max(bbox_fill, key=lambda x: x[0])[2]
    elif fill_polygons:
        fill_polygon = max(fill_polygons, key=lambda x: x[0])[2]

    outline_polygon = None
    outline_candidates = []
    for node in polygon_nodes:
        fill = re.search(r'fill\s*=\s*["\']([^"\']+)["\']', node, flags=re.IGNORECASE)
        stroke = re.search(
            r'stroke\s*=\s*["\']([^"\']+)["\']', node, flags=re.IGNORECASE
        )
        if not stroke:
            continue
        fill_is_none = fill and fill.group(1).strip().lower() == "none"
        if not fill_is_none:
            continue
        pts = re.search(r'points\s*=\s*["\']([^"\']*)["\']', node, flags=re.IGNORECASE)
        if not pts:
            continue
        points = _parse_points(pts.group(1))
        if len(points) < 3:
            continue
        area = _poly_area_abs(points)
        outline_candidates.append((area, node))
    if outline_candidates:
        outline_polygon = max(outline_candidates, key=lambda x: x[0])[1]

    return fill_polygon, outline_polygon


def _template_dimensions(text):
    vb_w = None
    vb_h = None
    vb = re.search(r"viewBox\s*=\s*['\"]([^'\"]+)['\"]", text, flags=re.IGNORECASE)
    if vb:
        vals = re.findall(r"[-+]?\d+(?:\.\d+)?", vb.group(1))
        if len(vals) >= 4:
            vb_w = float(vals[2])
            vb_h = float(vals[3])
    if vb_w is None or vb_h is None or vb_w <= 0 or vb_h <= 0:
        w = re.search(r'width\s*=\s*["\']([0-9.\-]+)', text, flags=re.IGNORECASE)
        h = re.search(r'height\s*=\s*["\']([0-9.\-]+)', text, flags=re.IGNORECASE)
        if w and h:
            try:
                vb_w = float(w.group(1))
                vb_h = float(h.group(1))
            except ValueError:
                vb_w = vb_h = None

    return vb_w, vb_h


def _extract_template_layers(template_svg: Path | None):
    if template_svg is None or not template_svg.exists():
        return None
    try:
        text = template_svg.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

    vb_w, vb_h = _template_dimensions(text)

    line_nodes = re.findall(r"<line\b[^>]*>", text, flags=re.IGNORECASE | re.DOTALL)
    polygon_nodes = re.findall(
        r"<polygon\b[^>]*>", text, flags=re.IGNORECASE | re.DOTALL
    )
    grid_x, grid_y = _collect_grid_from_lines(line_nodes)

    vertical_grid_line = None
    horizontal_grid_line = None
    for node in line_nodes:
        x1 = _parse_attr_float(node, "x1")
        x2 = _parse_attr_float(node, "x2")
        y1 = _parse_attr_float(node, "y1")
        y2 = _parse_attr_float(node, "y2")
        if x1 is None or x2 is None or y1 is None or y2 is None:
            continue
        if vertical_grid_line is None and abs(x2 - x1) <= 1.0 and abs(y2 - y1) > 1.0:
            x = (x1 + x2) / 2.0
            if vb_w is None or 0.0 <= x <= vb_w:
                vertical_grid_line = node
        if horizontal_grid_line is None and abs(y2 - y1) <= 1.0 and abs(x2 - x1) > 1.0:
            y = (y1 + y2) / 2.0
            if vb_h is None or 0.0 <= y <= vb_h:
                horizontal_grid_line = node

    fill_polygon, outline_polygon = _select_template_polygons(
        polygon_nodes, (vb_w, vb_h)
    )

    return {
        "lines": line_nodes,
        "fill_polygon": fill_polygon,
        "outline_polygon": outline_polygon,
        "vb_w": vb_w,
        "vb_h": vb_h,
        "grid_x": grid_x,
        "grid_y": grid_y,
        "vertical_grid_line": vertical_grid_line,
        "horizontal_grid_line": horizontal_grid_line,
    }
