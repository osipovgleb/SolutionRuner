#!/usr/bin/env python3
import argparse
import io
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import cv2
import numpy as np
import requests
from PIL import Image


GRAYSCALE_FILL_RGBA = np.asarray([153, 153, 153, 255], dtype=np.uint8)
EMBEDDED_GRID_RGBA = np.asarray([112, 112, 112, 255], dtype=np.uint8)
TRANSPARENT_BACKGROUND_RGBA = np.asarray([255, 255, 255, 0], dtype=np.uint8)
EXTERNAL_GRID_RGBA = np.asarray([0, 0, 0, 68], dtype=np.uint8)


def is_url(s: str) -> bool:
    p = urlparse(s)
    return p.scheme in {"http", "https"}


def load_image(src: str) -> tuple[np.ndarray, str]:
    if is_url(src):
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(src, headers=headers, timeout=60)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").lower()
        if "svg" in content_type:
            raise ValueError("source is not raster (svg)")
        data = resp.content
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        return np.array(img), content_type

    path = Path(src)
    img = Image.open(path).convert("RGBA")
    return np.array(img), str(path)


def extract_id(src: str) -> str:
    try:
        q = parse_qs(urlparse(src).query)
        if "id" in q and q["id"]:
            return q["id"][0]
    except Exception:
        pass
    return Path(src).stem


def contrast_mask(
    gray: np.ndarray,
    quantile: float = 0.97,
    alpha: np.ndarray | None = None,
    min_component_area: int = 20,
    close_px: int = 1,
) -> tuple[np.ndarray, dict]:
    gray = gray.astype(np.uint8)

    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    local_diff = cv2.absdiff(gray, blurred)
    smooth = cv2.GaussianBlur(local_diff, (3, 3), 0)

    hi = 80
    lo = 40
    edges = cv2.Canny(gray, lo, hi)

    th = float(np.quantile(smooth, quantile))
    mask = ((smooth > th).astype(np.uint8) * 255)
    mask = cv2.bitwise_or(mask, edges)

    if alpha is not None:
        alpha_mask = (alpha > 0).astype(np.uint8) * 255
        mask = cv2.bitwise_and(mask, alpha_mask)

    if close_px > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_px * 2 + 1, close_px * 2 + 1))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    filtered = np.zeros_like(mask)
    kept = []
    for i in range(1, num):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= min_component_area:
            c = (labels == i).astype(np.uint8) * 255
            kept.append((area,))
            filtered = cv2.bitwise_or(filtered, c)

    info = {
        "components_kept": len(kept),
        "quantile": quantile,
        "contrast_threshold": th,
        "areas": sorted([a for (a,) in kept], reverse=True),
    }
    return filtered, info


def infer_cell_size_from_svg(template_svg: Path | None = None, decimals: int = 3) -> float:
    if template_svg is None or not template_svg.exists():
        return 1.0

    try:
        text = template_svg.read_text(encoding="utf-8")
    except Exception:
        return 1.0

    line_nodes = re.findall(r"<line\b[^>]*>", text, flags=re.IGNORECASE | re.DOTALL)
    if not line_nodes:
        return 1.0

    def _extract_attr(node: str, key: str) -> float | None:
        m = re.search(rf'{key}\s*=\s*["\']([0-9.\-]+)["\']', node, flags=re.IGNORECASE)
        if not m:
            return None
        try:
            return float(m.group(1))
        except Exception:
            return None

    view_box = re.search(r'viewBox\s*=\s*["\']([^"\']+)["\']', text, flags=re.IGNORECASE)
    vb_w = vb_h = None
    if view_box:
        values = re.findall(r"[-+]?\d+(?:\.\d+)?", view_box.group(1))
        if len(values) >= 4:
            vb_w = float(values[2])
            vb_h = float(values[3])

    vx: list[float] = []
    vy: list[float] = []

    for node in line_nodes:
        x1 = _extract_attr(node, "x1")
        x2 = _extract_attr(node, "x2")
        y1 = _extract_attr(node, "y1")
        y2 = _extract_attr(node, "y2")
        if x1 is None or x2 is None or y1 is None or y2 is None:
            continue
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        if dx < 1.0 and dy > 1.0:
            x = (x1 + x2) / 2.0
            if vb_w is None or 0.0 <= x <= vb_w:
                vx.append(x)
        if dy < 1.0 and dx > 1.0:
            y = (y1 + y2) / 2.0
            if vb_h is None or 0.0 <= y <= vb_h:
                vy.append(y)

    if not vx or not vy:
        return 1.0

    def _cell(values: list[float]) -> float:
        vals = sorted({round(v, decimals) for v in values})
        if len(vals) < 2:
            return 1.0
        diffs = [b - a for a, b in zip(vals[:-1], vals[1:]) if b > a and b - a > 1.0]
        if not diffs:
            return 1.0
        return float(np.median(diffs))

    sx = _cell(vx)
    sy = _cell(vy)

    if sx <= 1.0 and sy <= 1.0:
        return 1.0
    if sx <= 1.0:
        return sy
    if sy <= 1.0:
        return sx
    detected = (sx + sy) / 2.0
    rounded = round(detected)
    return float(rounded if abs(detected - rounded) <= 0.75 else detected)


def largest_component(mask: np.ndarray) -> np.ndarray:
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num <= 1:
        return np.zeros_like(mask)

    max_area = -1
    max_label = 1
    for i in range(1, num):
        area = stats[i, cv2.CC_STAT_AREA]
        if area > max_area:
            max_area = area
            max_label = i

    return (labels == max_label).astype(np.uint8) * 255


def quad_from_mask(
    mask: np.ndarray,
    pad_cells: int = 2,
    cell_size: float = 1.0,
    width: int = 1,
    height: int = 1,
    expected_vertices: int | None = None,
) -> list[tuple[float, float]]:
    """Approximate the component using the requested polygon vertex count."""

    if expected_vertices not in {None, 3, 4}:
        raise ValueError("unsupported_polygon_vertex_count")
    ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return []

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []

    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) <= 0:
        return []

    hull = cv2.convexHull(contour)
    perimeter = cv2.arcLength(hull, True)
    pts = None
    hull_area = float(cv2.contourArea(hull))
    best_triangle = None
    for ratio in np.linspace(0.002, 0.03, 40):
        approx = cv2.approxPolyDP(hull, max(0.5, float(ratio) * perimeter), True)
        if len(approx) != 3:
            continue
        triangle = approx.reshape(-1, 2).astype(np.float64)
        coverage = float(cv2.contourArea(approx)) / hull_area if hull_area > 0 else 0.0
        if best_triangle is None or coverage > best_triangle[0]:
            best_triangle = (coverage, triangle)
        if expected_vertices != 4 and coverage >= 0.97:
            pts = triangle
            break

    if expected_vertices == 3 and pts is None and best_triangle is not None:
        pts = best_triangle[1]

    for ratio in np.linspace(0.002, 0.08, 80):
        if pts is not None:
            break
        if expected_vertices == 3:
            break
        approx = cv2.approxPolyDP(hull, max(0.5, float(ratio) * perimeter), True)
        if len(approx) == 4:
            pts = approx.reshape(-1, 2).astype(np.float64)
            break
    if pts is None and expected_vertices is None and best_triangle is not None:
        pts = best_triangle[1]
    if pts is None:
        return []

    center = pts.mean(axis=0)
    vectors = pts - center
    d = np.sqrt((vectors[:, 0] ** 2 + vectors[:, 1] ** 2))
    d[d == 0] = 1.0

    pad = max(0.0, float(pad_cells) * float(cell_size))
    if pad > 0:
        pts = center + vectors * ((d + pad) / d)[:, None]

    pts[:, 0] = np.clip(pts[:, 0], 0, max(0.0, float(width - 1)))
    pts[:, 1] = np.clip(pts[:, 1], 0, max(0.0, float(height - 1)))

    angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
    order = np.argsort(angles)
    pts = pts[order]
    start = np.argmin(pts[:, 1] * 10000.0 + pts[:, 0])
    pts = np.roll(pts, -start, axis=0)

    return [(float(x), float(y)) for x, y in pts]


def alpha_shape_mask(rgba: np.ndarray) -> tuple[np.ndarray, dict]:
    """Return the largest solid alpha component, excluding grid and small labels."""
    alpha = rgba[:, :, 3].astype(np.uint8)
    if int(alpha.max()) == int(alpha.min()):
        raise ValueError("alpha_channel_has_no_transparency")

    otsu_threshold, _ = cv2.threshold(
        alpha,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    threshold = int(np.clip(round(float(otsu_threshold)), 24, 224))
    solid = (alpha > threshold).astype(np.uint8) * 255
    component = largest_component(solid)
    if component.sum() == 0:
        raise ValueError("alpha_shape_not_found")

    component = cv2.morphologyEx(
        component,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    ys, xs = np.where(component > 0)
    return component, {
        "alpha_shape_threshold": threshold,
        "alpha_shape_pixels": int(len(xs)),
        "alpha_shape_bbox": (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
    }


def is_grayscale_source(rgba: np.ndarray) -> bool:
    rgb = rgba[:, :, :3].astype(np.int16)
    visible = rgba[:, :, 3] > 0
    if not bool(np.any(visible)):
        return False
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    return float(np.quantile(chroma[visible], 0.95)) <= 12.0


def restore_transparent_grayscale_source(
    rgba: np.ndarray,
) -> tuple[np.ndarray, dict[str, int]]:
    """Undo the two exact colors produced by drawing a grid below gray fill."""

    fill_mask = np.all(rgba == GRAYSCALE_FILL_RGBA, axis=2)
    embedded_grid_mask = np.all(rgba == EMBEDDED_GRID_RGBA, axis=2)
    fill_count = int(np.count_nonzero(fill_mask))
    embedded_grid_count = int(np.count_nonzero(embedded_grid_mask))
    if fill_count == 0:
        raise ValueError(
            "grayscale_fill_color_not_found: expected RGBA (153, 153, 153, 255)"
        )
    if embedded_grid_count == 0:
        raise ValueError(
            "embedded_grid_color_not_found: expected RGBA (112, 112, 112, 255)"
        )

    restored = rgba.copy()
    restored[fill_mask] = TRANSPARENT_BACKGROUND_RGBA
    restored[embedded_grid_mask] = EXTERNAL_GRID_RGBA
    return restored, {
        "fill_pixels_replaced": fill_count,
        "embedded_grid_pixels_replaced": embedded_grid_count,
    }


def grayscale_shape_mask(rgba: np.ndarray) -> tuple[np.ndarray, dict]:
    """Isolate the densest midtone region without selecting the connected grid."""

    gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)
    visible = rgba[:, :, 3] > 0
    lower = 30
    upper = 245
    eligible_values = gray[(gray > lower) & (gray < upper) & visible]
    if eligible_values.size == 0:
        raise ValueError("grayscale_shape_not_found")
    histogram = np.bincount(eligible_values, minlength=256)
    candidate_values = sorted(
        range(lower + 1, upper),
        key=lambda value: (-int(histogram[value]), value),
    )[:24]

    best = None
    tolerance = 6
    minimum_area = max(40, int(gray.size * 0.001))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    for center in candidate_values:
        if int(histogram[center]) == 0:
            continue
        band = (
            (np.abs(gray.astype(np.int16) - int(center)) <= tolerance) & visible
        ).astype(np.uint8) * 255
        band = cv2.morphologyEx(band, cv2.MORPH_CLOSE, kernel)
        count, labels, stats, _ = cv2.connectedComponentsWithStats(band, connectivity=8)
        for label in range(1, count):
            x = int(stats[label, cv2.CC_STAT_LEFT])
            y = int(stats[label, cv2.CC_STAT_TOP])
            width = int(stats[label, cv2.CC_STAT_WIDTH])
            height = int(stats[label, cv2.CC_STAT_HEIGHT])
            area = int(stats[label, cv2.CC_STAT_AREA])
            if area < minimum_area or width <= 1 or height <= 1:
                continue
            density = float(area) / float(width * height)
            if density < 0.12:
                continue
            score = float(area) * density
            rank = (score, density, area, -center, -label)
            if best is None or rank > best[0]:
                best = (rank, center, label, labels)
    if best is None:
        raise ValueError("grayscale_shape_not_found")
    _, selected_center, selected_label, selected_labels = best
    component = (selected_labels == selected_label).astype(np.uint8) * 255
    ys, xs = np.where(component > 0)
    return component, {
        "alpha_shape_threshold": f"gray_mode:{selected_center}+/-{tolerance}",
        "alpha_shape_pixels": int(len(xs)),
        "alpha_shape_bbox": (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
    }


def opaque_color_shape_mask(rgba: np.ndarray) -> tuple[np.ndarray, dict]:
    hsv = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2HSV)
    saturation_threshold = 20
    colored = (hsv[:, :, 1] > saturation_threshold).astype(np.uint8) * 255
    colored = cv2.morphologyEx(
        colored,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)),
    )
    colored = cv2.morphologyEx(
        colored,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
    )
    component = largest_component(colored)
    if component.sum() == 0:
        raise ValueError("opaque_color_shape_not_found")
    ys, xs = np.where(component > 0)
    return component, {
        "alpha_shape_threshold": f"saturation>{saturation_threshold}",
        "alpha_shape_pixels": int(len(xs)),
        "alpha_shape_bbox": (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())),
    }


def _projection_bands(signal: np.ndarray, vertical: bool) -> list[float]:
    """Find long semi-transparent bands; local marks cannot pass the coverage cutoff."""
    scores = signal.sum(axis=0 if vertical else 1).astype(np.float64)
    span = signal.shape[0] if vertical else signal.shape[1]
    peak = float(scores.max(initial=0.0))
    if peak <= 0:
        return []

    cutoff = max(10.0, float(span) * 0.16, peak * 0.32)
    selected = np.flatnonzero(scores >= cutoff)
    if selected.size == 0:
        return []

    groups: list[list[int]] = [[int(selected[0])]]
    for value in selected[1:]:
        value = int(value)
        if value - groups[-1][-1] <= 3:
            groups[-1].append(value)
        else:
            groups.append([value])

    centers: list[float] = []
    for group in groups:
        weights = scores[group]
        if float(weights.sum()) <= 0:
            continue
        centers.append(float(np.average(np.asarray(group, dtype=np.float64), weights=weights)))
    return centers


def _fit_grid_axis(
    centers: list[float],
    axis_size: int,
    preferred_step: float | None = None,
) -> dict:
    if len(centers) < 4:
        raise ValueError("not_enough_alpha_grid_lines")

    values = np.asarray(sorted(centers), dtype=np.float64)
    pairwise = np.asarray(
        [values[j] - values[i] for i in range(len(values)) for j in range(i + 1, len(values))],
        dtype=np.float64,
    )
    min_step = max(12.0, float(axis_size) * 0.04)
    max_step = float(axis_size) * 0.30
    usable = pairwise[(pairwise >= min_step) & (pairwise <= max_step)]
    if usable.size == 0:
        raise ValueError("alpha_grid_step_not_found")

    bin_width = max(1.5, float(axis_size) * 0.004)
    candidate_bins = Counter(map(int, np.rint(usable / bin_width).astype(int)))
    candidates = [float(key) * bin_width for key, _ in candidate_bins.most_common(20)]
    if preferred_step is not None:
        candidates = [
            candidate
            for candidate in candidates
            if preferred_step * 0.88 <= candidate <= preferred_step * 1.12
        ]
        if not candidates:
            candidates = [float(preferred_step)]

    best = None
    for candidate in candidates:
        tolerance = max(2.5, candidate * 0.085)
        for phase in values:
            lattice = np.rint((values - phase) / candidate).astype(int)
            residuals = np.abs(values - (phase + lattice * candidate))
            matched: dict[int, tuple[float, float]] = {}
            for value, index, residual in zip(values, lattice, residuals):
                if residual > tolerance:
                    continue
                index = int(index)
                current = matched.get(index)
                if current is None or residual < current[1]:
                    matched[index] = (float(value), float(residual))
            if len(matched) < 4:
                continue
            expected = max(1, int(round(float(axis_size) / candidate)) + 1)
            coverage = min(1.0, len(matched) / expected)
            score = (len(matched), coverage, -sum(item[1] for item in matched.values()))
            if best is None or score > best[0]:
                best = (score, candidate, matched)

    if best is None:
        raise ValueError("alpha_grid_phase_not_found")

    _, step_seed, matched = best
    lattice = np.asarray(sorted(matched), dtype=np.float64)
    matched_values = np.asarray([matched[int(index)][0] for index in lattice], dtype=np.float64)
    design = np.column_stack([np.ones_like(lattice), lattice])
    origin, step = np.linalg.lstsq(design, matched_values, rcond=None)[0]
    residuals = np.abs(matched_values - (origin + lattice * step))

    if step <= 0:
        raise ValueError("invalid_alpha_grid_step")
    return {
        "observed": [float(v) for v in values],
        "origin": float(origin),
        "step": float(step),
        "max_residual": float(residuals.max()) if residuals.size else 0.0,
        "mean_residual": float(residuals.mean()) if residuals.size else 0.0,
        "matched_count": int(len(matched)),
        "expected_count": int(max(1, round(float(axis_size) / float(step)) + 1)),
        "coverage": float(
            min(1.0, len(matched) / max(1, round(float(axis_size) / float(step)) + 1))
        ),
    }


def _square_step_candidates(
    x_centers: list[float],
    y_centers: list[float],
    width: int,
    height: int,
) -> list[tuple[float, float]]:
    """Return likely shared cell sizes and their deterministic vote weights."""
    shortest_axis = float(min(width, height))
    min_step = max(8.0, shortest_axis * 0.025)
    max_step = shortest_axis * 0.40
    quantum = max(0.25, shortest_axis * 0.0015)
    votes: Counter[int] = Counter()

    for centers in (x_centers, y_centers):
        values = np.asarray(sorted(centers), dtype=np.float64)
        if values.size < 2:
            continue

        for distance in np.diff(values):
            distance = float(distance)
            if min_step <= distance <= max_step:
                votes[int(round(distance / quantum))] += 2.0

        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                distance = float(values[j] - values[i])
                max_divisor = min(12, int(distance // min_step))
                for divisor in range(1, max_divisor + 1):
                    step = distance / float(divisor)
                    if min_step <= step <= max_step:
                        votes[int(round(step / quantum))] += 1.0 / np.sqrt(divisor)

        try:
            raw_axis = _fit_grid_axis(list(values), int(width if centers is x_centers else height))
        except ValueError:
            raw_axis = None
        if raw_axis is not None:
            raw_step = float(raw_axis["step"])
            for multiplier, weight in ((0.5, 2.0), (1.0, 6.0), (2.0, 3.0), (3.0, 1.5)):
                step = raw_step * multiplier
                if min_step <= step <= max_step:
                    votes[int(round(step / quantum))] += weight

    ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0]))[:120]
    return [(float(index) * quantum, float(weight)) for index, weight in ranked]


def _fit_axis_at_step(
    centers: list[float],
    axis_size: int,
    step: float,
) -> dict | None:
    """Fit one lattice phase while keeping the supplied shared cell size fixed."""
    if len(centers) < 4 or step <= 0:
        return None

    values = np.asarray(sorted(centers), dtype=np.float64)
    tolerance = max(1.5, min(6.0, float(step) * 0.11))
    best = None

    for anchor in values:
        indices = np.rint((values - anchor) / step).astype(int)
        initial_residuals = np.abs(values - (anchor + indices * step))
        matched: dict[int, tuple[float, float]] = {}
        for value, index, residual in zip(values, indices, initial_residuals):
            if float(residual) > tolerance:
                continue
            index = int(index)
            current = matched.get(index)
            if current is None or float(residual) < current[1]:
                matched[index] = (float(value), float(residual))
        if len(matched) < 4:
            continue

        matched_indices = np.asarray(sorted(matched), dtype=np.float64)
        matched_values = np.asarray(
            [matched[int(index)][0] for index in matched_indices],
            dtype=np.float64,
        )
        origin = float(np.median(matched_values - matched_indices * step))
        residuals = np.abs(matched_values - (origin + matched_indices * step))
        keep = residuals <= tolerance
        matched_indices = matched_indices[keep]
        matched_values = matched_values[keep]
        residuals = residuals[keep]
        if matched_values.size < 4:
            continue

        span_count = int(matched_indices.max() - matched_indices.min() + 1)
        span_coverage = float(matched_values.size / max(1, span_count))
        first_index = int(np.ceil((0.0 - origin) / step))
        last_index = int(np.floor((float(axis_size - 1) - origin) / step))
        full_count = max(1, last_index - first_index + 1)
        full_coverage = float(min(1.0, matched_values.size / full_count))
        normalized_residual = float(residuals.mean()) / step
        phase_score = (
            int(matched_values.size),
            span_coverage,
            full_coverage,
            -normalized_residual,
        )
        if best is None or phase_score > best[0]:
            best = (
                phase_score,
                origin,
                matched_indices.astype(int),
                matched_values,
                residuals,
                span_count,
                span_coverage,
                full_count,
                full_coverage,
            )

    if best is None:
        return None

    (
        _,
        origin,
        matched_indices,
        matched_values,
        residuals,
        span_count,
        span_coverage,
        full_count,
        full_coverage,
    ) = best
    return {
        "observed": [float(value) for value in values],
        "origin": float(origin),
        "step": float(step),
        "max_residual": float(residuals.max()) if residuals.size else 0.0,
        "mean_residual": float(residuals.mean()) if residuals.size else 0.0,
        "matched_count": int(matched_values.size),
        "expected_count": int(span_count),
        "coverage": float(span_coverage),
        "full_expected_count": int(full_count),
        "full_coverage": float(full_coverage),
        "_matched_indices": matched_indices,
        "_matched_values": matched_values,
    }


def _refine_shared_step(x_axis: dict, y_axis: dict, candidate_step: float) -> float:
    rows: list[list[float]] = []
    targets: list[float] = []
    for index, value in zip(x_axis["_matched_indices"], x_axis["_matched_values"]):
        rows.append([1.0, 0.0, float(index)])
        targets.append(float(value))
    for index, value in zip(y_axis["_matched_indices"], y_axis["_matched_values"]):
        rows.append([0.0, 1.0, float(index)])
        targets.append(float(value))
    if len(rows) < 8:
        return float(candidate_step)
    _, _, refined_step = np.linalg.lstsq(
        np.asarray(rows, dtype=np.float64),
        np.asarray(targets, dtype=np.float64),
        rcond=None,
    )[0]
    if refined_step <= 0 or abs(float(refined_step) / candidate_step - 1.0) > 0.12:
        return float(candidate_step)
    return float(refined_step)


def _fit_square_lattice(
    x_centers: list[float],
    y_centers: list[float],
    width: int,
    height: int,
    source: str,
) -> dict:
    """Fit x/y phases jointly under one square-grid cell-size constraint."""
    candidates = _square_step_candidates(x_centers, y_centers, width, height)
    if not candidates:
        raise ValueError("square_grid_step_not_found")

    max_vote = max(weight for _, weight in candidates)
    ranked_fits = []
    for candidate_step, vote in candidates:
        x_axis = _fit_axis_at_step(x_centers, width, candidate_step)
        y_axis = _fit_axis_at_step(y_centers, height, candidate_step)
        if x_axis is None or y_axis is None:
            continue

        refined_step = _refine_shared_step(x_axis, y_axis, candidate_step)
        x_axis = _fit_axis_at_step(x_centers, width, refined_step)
        y_axis = _fit_axis_at_step(y_centers, height, refined_step)
        if x_axis is None or y_axis is None:
            continue

        x_coverage = float(x_axis["coverage"])
        y_coverage = float(y_axis["coverage"])
        balanced_coverage = min(x_coverage, y_coverage)
        average_coverage = (x_coverage + y_coverage) / 2.0
        x_full_coverage = float(x_axis["full_coverage"])
        y_full_coverage = float(y_axis["full_coverage"])
        balanced_full_coverage = min(x_full_coverage, y_full_coverage)
        average_full_coverage = (x_full_coverage + y_full_coverage) / 2.0
        matched_total = int(x_axis["matched_count"]) + int(y_axis["matched_count"])
        residual_total = (
            float(x_axis["mean_residual"]) * int(x_axis["matched_count"])
            + float(y_axis["mean_residual"]) * int(y_axis["matched_count"])
        ) / max(1, matched_total)
        normalized_residual = residual_total / refined_step
        vote_score = float(vote / max_vote) if max_vote > 0 else 0.0
        score = (
            4.0 * balanced_coverage
            + 2.0 * average_coverage
            + 2.0 * balanced_full_coverage
            + 1.0 * average_full_coverage
            + 0.30 * min(18, matched_total)
            - 6.0 * normalized_residual
            + 0.50 * vote_score
        )
        ranked_fits.append(
            (
                score,
                balanced_coverage,
                matched_total,
                -normalized_residual,
                refined_step,
                x_axis,
                y_axis,
            )
        )

    if not ranked_fits:
        raise ValueError("square_grid_lattice_not_found")

    ranked_fits.sort(key=lambda item: item[:5], reverse=True)
    score, balanced_coverage, matched_total, neg_residual, step, x_axis, y_axis = ranked_fits[0]
    normalized_residual = -float(neg_residual)
    average_coverage = (float(x_axis["coverage"]) + float(y_axis["coverage"])) / 2.0
    average_full_coverage = (
        float(x_axis["full_coverage"]) + float(y_axis["full_coverage"])
    ) / 2.0
    confidence = float(
        np.clip(
            0.35 * balanced_coverage
            + 0.25 * average_coverage
            + 0.15 * average_full_coverage
            + 0.25 * max(0.0, 1.0 - normalized_residual / 0.10),
            0.0,
            1.0,
        )
    )
    if confidence < 0.52 or matched_total < 8 or normalized_residual > 0.10:
        raise ValueError(
            "square_grid_low_confidence:"
            f" confidence={confidence:.3f}"
            f" matched={matched_total}"
            f" residual={normalized_residual:.3f}"
        )

    for axis in (x_axis, y_axis):
        axis.pop("_matched_indices", None)
        axis.pop("_matched_values", None)

    return {
        "source": source,
        "x": x_axis,
        "y": y_axis,
        "cell": float(step),
        "confidence": confidence,
        "joint_score": float(score),
        "correction": "joint_square_lattice",
    }


def _promote_clean_grid_fundamental(
    centers: list[float],
    axis_size: int,
    axis: dict,
) -> tuple[dict, int]:
    """Replace a noisy shared subharmonic with its clean repeated fundamental."""

    step = float(axis["step"])
    normalized_residual = float(axis.get("max_residual", 0.0)) / step
    if normalized_residual < 0.065:
        return axis, 1

    minimum_coverage = min(0.60, float(axis.get("coverage", 0.0)) * 0.65)
    promoted: list[tuple[float, float, int, dict]] = []
    for multiplier in (2, 3, 4):
        preferred = step * multiplier
        if preferred > float(axis_size) * 0.30:
            continue
        try:
            candidate = _fit_grid_axis(centers, axis_size, preferred_step=preferred)
        except ValueError:
            continue
        candidate_step = float(candidate["step"])
        candidate_residual = float(candidate.get("max_residual", 0.0)) / candidate_step
        candidate_coverage = float(candidate.get("coverage", 0.0))
        if (
            int(candidate.get("matched_count", 0)) >= 4
            and candidate_residual <= 0.055
            and candidate_residual <= normalized_residual * 0.5
            and candidate_coverage >= minimum_coverage
            and abs(candidate_step / preferred - 1.0) <= 0.10
        ):
            promoted.append(
                (candidate_coverage, -candidate_residual, multiplier, candidate)
            )
    if not promoted:
        return axis, 1
    _, _, multiplier, candidate = max(promoted, key=lambda item: item[:3])
    return candidate, multiplier


def infer_grid_from_alpha(rgba: np.ndarray, shape_threshold: int) -> dict:
    """Infer the full orthogonal lattice only from semi-transparent pixels."""
    alpha = rgba[:, :, 3].astype(np.uint8)
    semi_transparent = (alpha > 0) & (alpha <= max(1, shape_threshold))
    x_centers = _projection_bands(semi_transparent, vertical=True)
    y_centers = _projection_bands(semi_transparent, vertical=False)
    return _fit_square_lattice(
        x_centers,
        y_centers,
        rgba.shape[1],
        rgba.shape[0],
        source="alpha",
    )


def infer_grid_from_grayscale(rgba: np.ndarray) -> dict:
    gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY).astype(np.int16)
    vertical_response = np.zeros_like(gray)
    horizontal_response = np.zeros_like(gray)
    vertical_response[:, 1:-1] = np.abs(
        2 * gray[:, 1:-1] - gray[:, :-2] - gray[:, 2:]
    )
    horizontal_response[1:-1, :] = np.abs(
        2 * gray[1:-1, :] - gray[:-2, :] - gray[2:, :]
    )
    x_centers = _projection_bands(vertical_response > 8, vertical=True)
    y_centers = _projection_bands(horizontal_response > 8, vertical=False)
    return _fit_square_lattice(
        x_centers,
        y_centers,
        rgba.shape[1],
        rgba.shape[0],
        source="grayscale",
    )


def infer_grid_from_opaque_color(rgba: np.ndarray) -> dict:
    rgb = rgba[:, :, :3]
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    neutral_dark_lines = (gray < 210) & (hsv[:, :, 1] < 40)
    x_centers = _projection_bands(neutral_dark_lines, vertical=True)
    y_centers = _projection_bands(neutral_dark_lines, vertical=False)

    gray_i16 = gray.astype(np.int16)
    if len(x_centers) < 4:
        vertical_response = np.zeros_like(gray_i16)
        vertical_response[:, 1:-1] = np.abs(
            2 * gray_i16[:, 1:-1] - gray_i16[:, :-2] - gray_i16[:, 2:]
        )
        x_centers = _projection_bands(vertical_response > 8, vertical=True)
    if len(y_centers) < 4:
        horizontal_response = np.zeros_like(gray_i16)
        horizontal_response[1:-1, :] = np.abs(
            2 * gray_i16[1:-1, :] - gray_i16[:-2, :] - gray_i16[2:, :]
        )
        y_centers = _projection_bands(horizontal_response > 8, vertical=False)

    return _fit_square_lattice(
        x_centers,
        y_centers,
        rgba.shape[1],
        rgba.shape[0],
        source="opaque-color",
    )


def _snap_quad_to_alpha_grid(
    quad: list[tuple[float, float]],
    grid: dict,
) -> tuple[list[tuple[float, float]], list[tuple[int, int]]]:
    snapped: list[tuple[float, float]] = []
    indices: list[tuple[int, int]] = []
    x_origin = float(grid["x"]["origin"])
    y_origin = float(grid["y"]["origin"])
    x_step = float(grid["x"]["step"])
    y_step = float(grid["y"]["step"])

    for x, y in quad:
        ix = int(round((x - x_origin) / x_step))
        iy = int(round((y - y_origin) / y_step))
        indices.append((ix, iy))
        snapped.append((x_origin + ix * x_step, y_origin + iy * y_step))

    if len(indices) not in {3, 4}:
        raise ValueError("unsupported_polygon_vertex_count")
    if len(set(indices)) != len(indices):
        raise ValueError("alpha_grid_vertices_are_not_unique")
    return snapped, indices


def _select_grid_for_quad(quad: list[tuple[float, float]], grids: list[dict]) -> dict:
    """Choose the lattice that best explains both its lines and shape corners."""
    scored: list[tuple[float, dict, float]] = []
    candidate_scores: dict[str, dict[str, float]] = {}

    for grid in grids:
        x_origin = float(grid["x"]["origin"])
        y_origin = float(grid["y"]["origin"])
        x_step = float(grid["x"]["step"])
        y_step = float(grid["y"]["step"])
        residuals: list[float] = []

        for x, y in quad:
            ix = round((x - x_origin) / x_step)
            iy = round((y - y_origin) / y_step)
            dx = (x - (x_origin + ix * x_step)) / x_step
            dy = (y - (y_origin + iy * y_step)) / y_step
            residuals.append(float(np.hypot(dx, dy)))

        fit_error = float(np.mean(residuals))
        max_fit_error = float(max(residuals))
        confidence = float(grid.get("confidence", 0.0))
        score = confidence - fit_error - 0.25 * max_fit_error
        source = str(grid.get("source", "unknown"))
        candidate_scores[source] = {
            "confidence": confidence,
            "quad_fit_error": fit_error,
            "quad_max_fit_error": max_fit_error,
            "selection_score": score,
        }
        scored.append((score, grid, fit_error))

    if not scored:
        raise ValueError("grid_candidates_not_found")

    _, selected, fit_error = max(scored, key=lambda item: item[0])
    result = dict(selected)
    result["quad_fit_error"] = fit_error
    result["candidate_scores"] = candidate_scores
    return result


def _measure_axis_step(axis: dict) -> float:
    """Measure one axis from its own lines; use the shared step only for numbering."""
    observed = [float(value) for value in axis["observed"]]
    origin = float(axis["origin"])
    reference_step = float(axis["step"])
    closest_by_index: dict[int, tuple[float, float]] = {}

    for value in observed:
        index = int(round((value - origin) / reference_step))
        predicted = origin + index * reference_step
        residual = abs(value - predicted)
        previous = closest_by_index.get(index)
        if previous is None or residual < previous[0]:
            closest_by_index[index] = (residual, value)

    selected: list[tuple[int, float]] = []
    for tolerance_ratio in (0.06, 0.10, 0.18, 0.30, 0.50):
        tolerance = max(1.5, reference_step * tolerance_ratio)
        selected = sorted(
            (index, value)
            for index, (residual, value) in closest_by_index.items()
            if residual <= tolerance
        )
        if len(selected) >= 3:
            break

    if len(selected) < 2:
        selected = sorted(
            (index, value)
            for index, (_, value) in closest_by_index.items()
        )

    slopes = [
        (right_value - left_value) / (right_index - left_index)
        for pos, (left_index, left_value) in enumerate(selected)
        for right_index, right_value in selected[pos + 1 :]
        if right_index != left_index
    ]
    plausible = [
        value
        for value in slopes
        if reference_step * 0.75 <= value <= reference_step * 1.25
    ]
    if plausible:
        return float(np.median(plausible))
    if slopes:
        return float(np.median(slopes))
    return reference_step


def _source_grid_coordinates(
    grid_indices: list[tuple[int, int]],
    grid: dict,
) -> list[tuple[int, int]]:
    x_axis = grid["x"]
    y_axis = grid["y"]
    if grid.get("coordinate_anchor") == "canvas":
        x_zero = int(round(-float(x_axis["origin"]) / float(x_axis["step"])))
        source_height = float(grid["source_height"])
        y_zero = int(
            round(
                (source_height - float(y_axis["origin"]))
                / float(y_axis["step"])
            )
        )
        return [(int(ix - x_zero), int(y_zero - iy)) for ix, iy in grid_indices]

    x_observed_indices = [
        int(round((float(value) - float(x_axis["origin"])) / float(x_axis["step"])))
        for value in x_axis["observed"]
    ]
    y_observed_indices = [
        int(round((float(value) - float(y_axis["origin"])) / float(y_axis["step"])))
        for value in y_axis["observed"]
    ]
    x_zero = min(x_observed_indices)
    y_zero = max(y_observed_indices)
    return [(int(ix - x_zero), int(y_zero - iy)) for ix, iy in grid_indices]


def _fmt_num(v: float) -> str:
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
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
    except Exception:
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
        vals = sorted(set(round(v, 4) for v in vals))
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
        sx = sorted(set(round(x, 4) for x in grid_x))
        # force pair for symmetry in rare cases
        if abs(left_x - right_x) < 1e-6 and len(sx) >= 2:
            right_x = sx[1] if sx[0] == left_x else sx[0]

    if grid_y:
        top_y = min(grid_y, key=lambda y: abs(y - min(ys)))
        bot_y = min(grid_y, key=lambda y: abs(y - max(ys)))
        sy = sorted(set(round(y, 4) for y in grid_y))
        if abs(top_y - bot_y) < 1e-6 and len(sy) >= 2:
            bot_y = sy[1] if sy[0] == top_y else sy[0]

    idx_by_y = sorted(range(4), key=lambda i: ys[i])
    top_set = set(idx_by_y[:2])
    bot_set = set(idx_by_y[2:])

    idx_by_x = sorted(range(4), key=lambda i: xs[i])
    left_set = set(idx_by_x[:2])
    right_set = set(idx_by_x[2:])

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


def _infer_grid_from_gray(gray: np.ndarray, comp_bbox: tuple[float, float, float, float] | None = None) -> tuple[list[float], list[float]]:
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
        vals = sorted(set(round(v, 3) for v in vals))
        out = [vals[0]]
        for v in vals[1:]:
            if abs(v - out[-1]) >= eps:
                out.append(v)
        return out

    return _dedup(xs), _dedup(ys)


def _extract_template_layers(template_svg: Path | None):
    if template_svg is None or not template_svg.exists():
        return None
    try:
        text = template_svg.read_text(encoding="utf-8")
    except Exception:
        return None

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
            except Exception:
                vb_w = vb_h = None

    line_nodes = re.findall(r"<line\b[^>]*>", text, flags=re.IGNORECASE | re.DOTALL)
    polygon_nodes = re.findall(r"<polygon\b[^>]*>", text, flags=re.IGNORECASE | re.DOTALL)
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
            in_box = (minx >= -1e-6 and maxx <= vb_w + 1e-6 and miny >= -1e-6 and maxy <= vb_h + 1e-6)
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
        stroke = re.search(r'stroke\s*=\s*["\']([^"\']+)["\']', node, flags=re.IGNORECASE)
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
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        out.append(f"M{_fmt_num(x1)},{_fmt_num(y1)} L{_fmt_num(x2)},{_fmt_num(y2)}")
    return out


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
    comp = largest_component(mask)
    if comp.sum() == 0:
        raise ValueError("no_contours")

    ys, xs = np.where(comp > 0)
    comp_bbox = (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max()))

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
    snapped_source_quad, grid_indices = _snap_quad_to_alpha_grid(source_quad, alpha_grid)
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
            '</g>\n'
        )

    if template and template.get("outline_polygon"):
        svg += f"  {_replace_points(template['outline_polygon'], points_attr)}\n"
    else:
        svg += '<g id="prototype-sections" fill="none" stroke="#000" stroke-width="1">\n'
        for i, p in enumerate(edge_paths):
            svg += f'  <path id="edge-{i}" d="{p}"/>\n'
        svg += '  </g>\n'

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
        '1 &#1089;&#1084;</text>\n'
    )
    svg += '</g>\n'

    svg += '</svg>\n'
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
) -> Path:
    rgba, source_info = load_image(src)
    preprocessing_info: dict[str, int] | None = None
    if is_grayscale_source(rgba):
        rgba, preprocessing_info = restore_transparent_grayscale_source(rgba)
        out_dir.mkdir(parents=True, exist_ok=True)
        restored_path = out_dir / f"{extract_id(src)}.transparent-fill.png"
        Image.fromarray(rgba, mode="RGBA").save(restored_path)

    alpha = rgba[:, :, 3]
    gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)

    source_info_text = str(source_info)
    if source_info_text.lower().startswith("image/"):
        raw_format = source_info_text.split("/", 1)[1].split(";", 1)[0]
    else:
        raw_format = Path(source_info_text).suffix.lstrip(".")
        if not raw_format:
            raw_format = Path(urlparse(src).path).suffix.lstrip(".")
    raw_format_lower = raw_format.lower()
    if "bmp" in raw_format_lower:
        image_format = "BMP"
    elif raw_format_lower in {"jpg", "jpeg", "pjpeg"}:
        image_format = "JPEG"
    elif raw_format_lower:
        image_format = raw_format_lower.upper()
    else:
        image_format = "UNKNOWN"

    h, w = gray.shape
    if is_grayscale_source(rgba):
        base_mask, alpha_info = grayscale_shape_mask(rgba)
        alpha_grid = infer_grid_from_grayscale(rgba)
    elif not bool(np.any(alpha < 250)):
        base_mask, alpha_info = opaque_color_shape_mask(rgba)
        alpha_grid = infer_grid_from_opaque_color(rgba)
    else:
        base_mask, alpha_info = alpha_shape_mask(rgba)
        grid_candidates = [
            infer_grid_from_alpha(rgba, alpha_info["alpha_shape_threshold"])
        ]
        try:
            grid_candidates.append(infer_grid_from_grayscale(rgba))
        except ValueError:
            pass

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

    shape_pixels = rgba[:, :, :3][base_mask > 0].astype(np.float32)
    if shape_pixels.size == 0:
        visual_type = "unknown"
    else:
        median_r, median_g, median_b = np.median(shape_pixels, axis=0)
        if max(median_r, median_g, median_b) - min(median_r, median_g, median_b) <= 12:
            visual_type = "grayscale"
        elif median_b >= median_r + 20 and median_b >= median_g + 10:
            visual_type = "blue"
        else:
            visual_type = "color"

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

    integer_quad = [(int(round(x)), int(round(y))) for x, y in quad]
    source_polygon_points = sorted(
        proto_info["source_grid_points"],
        key=lambda point: (point[1], point[0]),
    )
    detected_x_step = _measure_axis_step(alpha_grid["x"])
    detected_y_step = _measure_axis_step(alpha_grid["y"])
    print(f"polygon_points={source_polygon_points}")
    print(f"svg_polygon_points={integer_quad}")
    print(f"image_format={image_format}")
    print(f"visual_type={visual_type}")
    print(f"grid_step_x={_fmt_num(detected_x_step)}")
    print(f"grid_step_y={_fmt_num(detected_y_step)}")
    print(f"grid_step_shared={_fmt_num(float(alpha_grid['cell']))}")

    with open(out.with_suffix('.txt'), 'w', encoding='utf-8') as f:
        f.write(f"source={src}\n")
        if preprocessing_info is not None:
            f.write(
                "fill_pixels_replaced="
                f"{preprocessing_info['fill_pixels_replaced']}\n"
            )
            f.write(
                "embedded_grid_pixels_replaced="
                f"{preprocessing_info['embedded_grid_pixels_replaced']}\n"
            )
        f.write(f"size={w}x{h}\n")
        f.write(f"mask_pixels={int(base_mask.sum()//255)}\n")
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
        f.write(f"source_quad_on_alpha_grid={proto_info['source_quad_on_alpha_grid']}\n")
        f.write(f"grid_indices={proto_info['grid_indices']}\n")
        f.write(f"source_polygon_points={source_polygon_points}\n")
        f.write(f"grid_bounds={proto_info['grid_bounds']}\n")
        f.write(f"svg_size={proto_info['svg_size']}\n")

    return out


def main():
    p = argparse.ArgumentParser(description="Deterministic PNG -> SVG from an alpha-channel grid")
    p.add_argument("source", help="Path or URL to a raster image")
    p.add_argument("--out-dir", type=Path, default=Path("svg_from_contrast"))
    p.add_argument("--pad-cells", type=int, default=2, help="Pad in cell units (2 by default)")
    p.add_argument(
        "--cell-size",
        type=float,
        default=None,
        help="Cell size in pixels. If omitted and --template-svg is set, detect from template.",
    )
    p.add_argument(
        "--template-svg",
        type=Path,
        default=Path(__file__).resolve().with_name("template_from_lessons.svg"),
        help="SVG template used for cell size, grid style, fill, and outline.",
    )
    p.add_argument(
        "--auto-grid",
        action="store_true",
        help="Deprecated compatibility flag; the grid is always inferred from alpha.",
    )
    p.add_argument(
        "--no-template-grid",
        action="store_true",
        help="Do not copy <line> grid from template into result.",
    )
    p.add_argument("--quantile", type=float, default=0.97, help="Contrast quantile from 0.0 to 1.0")
    p.add_argument("--min-area", type=int, default=20, help="Minimum component area")
    p.add_argument("--close", type=int, default=1, help="Morphological close radius")
    p.add_argument(
        "--simplify",
        type=float,
        default=1.5,
        help="Unused for quad mode (kept for backward compatibility)",
    )
    args = p.parse_args()

    out = run(
        args.source,
        args.out_dir,
        args.pad_cells,
        args.quantile,
        args.min_area,
        args.close,
        args.simplify,
        not args.no_template_grid,
        args.cell_size,
        args.template_svg,
        args.auto_grid,
    )
    print(out)


if __name__ == "__main__":
    main()
