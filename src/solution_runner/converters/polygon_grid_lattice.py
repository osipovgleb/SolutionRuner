"""Fit and refine a square lattice in a raster image."""

import numpy as np

if __package__:
    from .polygon_grid_axis import _fit_grid_axis, _square_step_candidates
else:
    from polygon_grid_axis import _fit_grid_axis, _square_step_candidates


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
    score, balanced_coverage, matched_total, neg_residual, step, x_axis, y_axis = (
        ranked_fits[0]
    )
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
