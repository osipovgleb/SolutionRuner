"""Identify regularly spaced grid bands and possible cell sizes."""

import itertools
from collections import Counter

import numpy as np


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
        centers.append(
            float(np.average(np.asarray(group, dtype=np.float64), weights=weights))
        )
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
        [
            values[j] - values[i]
            for i in range(len(values))
            for j in range(i + 1, len(values))
        ],
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
            expected = max(1, round(float(axis_size) / candidate) + 1)
            coverage = min(1.0, len(matched) / expected)
            score = (len(matched), coverage, -sum(item[1] for item in matched.values()))
            if best is None or score > best[0]:
                best = (score, candidate, matched)

    if best is None:
        raise ValueError("alpha_grid_phase_not_found")

    _, _step_seed, matched = best
    lattice = np.asarray(sorted(matched), dtype=np.float64)
    matched_values = np.asarray(
        [matched[int(index)][0] for index in lattice], dtype=np.float64
    )
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
        "matched_count": len(matched),
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
                votes[round(distance / quantum)] += 2.0

        for left, right in itertools.combinations(values, 2):
            distance = float(right - left)
            max_divisor = min(12, int(distance // min_step))
            for divisor in range(1, max_divisor + 1):
                step = distance / float(divisor)
                if min_step <= step <= max_step:
                    votes[round(step / quantum)] += 1.0 / np.sqrt(divisor)

        try:
            raw_axis = _fit_grid_axis(
                list(values), int(width if centers is x_centers else height)
            )
        except ValueError:
            raw_axis = None
        if raw_axis is not None:
            raw_step = float(raw_axis["step"])
            for multiplier, weight in ((0.5, 2.0), (1.0, 6.0), (2.0, 3.0), (3.0, 1.5)):
                step = raw_step * multiplier
                if min_step <= step <= max_step:
                    votes[round(step / quantum)] += weight

    ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0]))[:120]
    return [(float(index) * quantum, float(weight)) for index, weight in ranked]
