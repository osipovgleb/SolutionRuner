"""Infer polygon grid coordinates from image channels."""

import cv2
import numpy as np

if __package__:
    from .polygon_grid_axis import _projection_bands
    from .polygon_grid_lattice import _fit_square_lattice
else:
    from polygon_grid_axis import _projection_bands
    from polygon_grid_lattice import _fit_square_lattice


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
    vertical_response[:, 1:-1] = np.abs(2 * gray[:, 1:-1] - gray[:, :-2] - gray[:, 2:])
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
        ix = round((x - x_origin) / x_step)
        iy = round((y - y_origin) / y_step)
        indices.append((ix, iy))
        snapped.append((x_origin + ix * x_step, y_origin + iy * y_step))

    if len(indices) not in {3, 4}:
        raise ValueError("unsupported_polygon_vertex_count")
    if len(set(indices)) != len(indices):
        raise ValueError("alpha_grid_vertices_are_not_unique")
    return snapped, indices


def _measure_axis_step(axis: dict) -> float:
    """Measure one axis from its own lines; use the shared step only for numbering."""
    observed = [float(value) for value in axis["observed"]]
    origin = float(axis["origin"])
    reference_step = float(axis["step"])
    closest_by_index: dict[int, tuple[float, float]] = {}

    for value in observed:
        index = round((value - origin) / reference_step)
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
            (index, value) for index, (_, value) in closest_by_index.items()
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
        x_zero = round(-float(x_axis["origin"]) / float(x_axis["step"]))
        source_height = float(grid["source_height"])
        y_zero = round(
            (source_height - float(y_axis["origin"])) / float(y_axis["step"])
        )
        return [(int(ix - x_zero), int(y_zero - iy)) for ix, iy in grid_indices]

    x_observed_indices = [
        round((float(value) - float(x_axis["origin"])) / float(x_axis["step"]))
        for value in x_axis["observed"]
    ]
    y_observed_indices = [
        round((float(value) - float(y_axis["origin"])) / float(y_axis["step"]))
        for value in y_axis["observed"]
    ]
    x_zero = min(x_observed_indices)
    y_zero = max(y_observed_indices)
    return [(int(ix - x_zero), int(y_zero - iy)) for ix, iy in grid_indices]


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
