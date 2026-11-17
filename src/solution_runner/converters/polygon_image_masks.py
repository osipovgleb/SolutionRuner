"""Extract foreground masks and template scale from polygon images."""

import itertools
import re
from pathlib import Path

import cv2
import numpy as np


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
    mask = (smooth > th).astype(np.uint8) * 255
    mask = cv2.bitwise_or(mask, edges)

    if alpha is not None:
        alpha_mask = (alpha > 0).astype(np.uint8) * 255
        mask = cv2.bitwise_and(mask, alpha_mask)

    if close_px > 0:
        k = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (close_px * 2 + 1, close_px * 2 + 1)
        )
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


def infer_cell_size_from_svg(
    template_svg: Path | None = None, decimals: int = 3
) -> float:
    if template_svg is None or not template_svg.exists():
        return 1.0

    try:
        text = template_svg.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
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
        except ValueError:
            return None

    view_box = re.search(
        r'viewBox\s*=\s*["\']([^"\']+)["\']', text, flags=re.IGNORECASE
    )
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
        diffs = [b - a for a, b in itertools.pairwise(vals) if b > a and b - a > 1.0]
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
        "alpha_shape_pixels": len(xs),
        "alpha_shape_bbox": (
            int(xs.min()),
            int(ys.min()),
            int(xs.max()),
            int(ys.max()),
        ),
    }


def is_grayscale_source(rgba: np.ndarray) -> bool:
    rgb = rgba[:, :, :3].astype(np.int16)
    visible = rgba[:, :, 3] > 0
    if not bool(np.any(visible)):
        return False
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    return float(np.quantile(chroma[visible], 0.95)) <= 12.0


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
        "alpha_shape_pixels": len(xs),
        "alpha_shape_bbox": (
            int(xs.min()),
            int(ys.min()),
            int(xs.max()),
            int(ys.max()),
        ),
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
        "alpha_shape_pixels": len(xs),
        "alpha_shape_bbox": (
            int(xs.min()),
            int(ys.min()),
            int(xs.max()),
            int(ys.max()),
        ),
    }
