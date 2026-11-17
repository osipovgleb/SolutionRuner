"""Approximate polygon contours for each source-image mode."""

import cv2
import numpy as np


def _stable_ordered_contour_polygon(
    contour: np.ndarray,
    expected_vertices: int,
) -> np.ndarray | None:
    """Return the most stable vertex approximation in contour traversal order."""

    perimeter = cv2.arcLength(contour, True)
    candidates: dict[
        tuple[tuple[int, int], ...],
        tuple[int, float],
    ] = {}
    contour_area = abs(float(cv2.contourArea(contour)))
    for ratio in np.linspace(0.002, 0.08, 80):
        approx = cv2.approxPolyDP(
            contour,
            max(0.5, float(ratio) * perimeter),
            True,
        )
        if len(approx) != expected_vertices:
            continue
        points = approx.reshape(-1, 2)
        start = min(
            range(expected_vertices),
            key=lambda index: (int(points[index][1]), int(points[index][0])),
        )
        ordered = np.roll(points, -start, axis=0)
        key = tuple((int(x), int(y)) for x, y in ordered)
        count, _ = candidates.get(key, (0, 0.0))
        area_error = abs(abs(float(cv2.contourArea(ordered))) - contour_area)
        candidates[key] = (count + 1, area_error)
    if not candidates:
        return None
    points, _ = max(
        candidates.items(),
        key=lambda item: (item[1][0], -item[1][1]),
    )
    return np.asarray(points, dtype=np.float64)


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
    _ys, xs = np.where(mask > 0)
    if len(xs) == 0:
        return []

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []

    contour = max(contours, key=cv2.contourArea)
    if cv2.contourArea(contour) <= 0:
        return []

    preserve_contour_order = expected_vertices == 4
    if preserve_contour_order:
        pts = _stable_ordered_contour_polygon(contour, 4)
    else:
        pts = None
        hull = cv2.convexHull(contour)
        perimeter = cv2.arcLength(hull, True)
        hull_area = float(cv2.contourArea(hull))
        best_triangle = None
        for ratio in np.linspace(0.002, 0.03, 40):
            approx = cv2.approxPolyDP(
                hull,
                max(0.5, float(ratio) * perimeter),
                True,
            )
            if len(approx) != 3:
                continue
            triangle = approx.reshape(-1, 2).astype(np.float64)
            coverage = (
                float(cv2.contourArea(approx)) / hull_area if hull_area > 0 else 0.0
            )
            if best_triangle is None or coverage > best_triangle[0]:
                best_triangle = (coverage, triangle)
            if coverage >= 0.97:
                pts = triangle
                break

        if expected_vertices == 3 and pts is None and best_triangle is not None:
            pts = best_triangle[1]

        for ratio in np.linspace(0.002, 0.08, 80):
            if pts is not None or expected_vertices == 3:
                break
            approx = cv2.approxPolyDP(
                hull,
                max(0.5, float(ratio) * perimeter),
                True,
            )
            if len(approx) == 4:
                pts = approx.reshape(-1, 2).astype(np.float64)
                break
        if pts is None and expected_vertices is None and best_triangle is not None:
            pts = best_triangle[1]
    if pts is None:
        return []

    center = pts.mean(axis=0)
    vectors = pts - center
    d = np.sqrt(vectors[:, 0] ** 2 + vectors[:, 1] ** 2)
    d[d == 0] = 1.0

    pad = max(0.0, float(pad_cells) * float(cell_size))
    if pad > 0:
        pts = center + vectors * ((d + pad) / d)[:, None]

    pts[:, 0] = np.clip(pts[:, 0], 0, max(0.0, float(width - 1)))
    pts[:, 1] = np.clip(pts[:, 1], 0, max(0.0, float(height - 1)))

    if not preserve_contour_order:
        angles = np.arctan2(pts[:, 1] - center[1], pts[:, 0] - center[0])
        order = np.argsort(angles)
        pts = pts[order]
    start = np.argmin(pts[:, 1] * 10000.0 + pts[:, 0])
    pts = np.roll(pts, -start, axis=0)

    return [(float(x), float(y)) for x, y in pts]


def transparent_quad_from_mask(
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
    _ys, xs = np.where(mask > 0)
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
    d = np.sqrt(vectors[:, 0] ** 2 + vectors[:, 1] ** 2)
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


def ring_quad_from_mask(
    mask: np.ndarray,
    pad_cells: int = 2,
    cell_size: float = 1.0,
    width: int = 1,
    height: int = 1,
) -> list[tuple[float, float]]:
    _ys, xs = np.where(mask > 0)
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
        if coverage >= 0.97:
            pts = triangle
            break

    for ratio in np.linspace(0.002, 0.08, 80):
        if pts is not None:
            break
        approx = cv2.approxPolyDP(hull, max(0.5, float(ratio) * perimeter), True)
        if len(approx) == 4:
            pts = approx.reshape(-1, 2).astype(np.float64)
            break
    if pts is None and best_triangle is not None:
        pts = best_triangle[1]
    if pts is None:
        return []

    center = pts.mean(axis=0)
    vectors = pts - center
    d = np.sqrt(vectors[:, 0] ** 2 + vectors[:, 1] ** 2)
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
