"""Fit derivative graphs with source-supported tangent contacts at grid levels."""

import hashlib
import io
from dataclasses import replace

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from ..probability.common import UnsupportedCondition
from . import derivative_level_trace as primitive_trace
from . import primitive_bezier
from .primitive_curves import _dense, detect, verify


def recover(data, question):
    """Recover a source-bound curve; persistent exact-byte reuse lives in the adapter."""
    return _recover_new(data, question)


def _pin_extrema(logical, points, question):
    # A smoothed cap can shrink away from a grid line. Snap only when the
    # original traced ink, before smoothing, actually reaches that grid level.
    pinned = []
    for index, p in enumerate(points):
        window = logical[np.abs(logical[:, 0] - p.x) <= 0.18, 1]
        raw_y = float(window.max() if p.kind == "maximum" else window.min())
        target = (
            float(question.horizontal)
            if question.horizontal is not None
            else float(round(raw_y))
        )
        previous_y = logical[0, 1] if index == 0 else points[index - 1].y
        following_y = (
            logical[-1, 1] if index == len(points) - 1 else points[index + 1].y
        )
        retains_turn = (
            target > max(previous_y, following_y) + 0.01
            if p.kind == "maximum"
            else target < min(previous_y, following_y) - 0.01
        )
        if retains_turn and abs(raw_y - target) <= 0.12 and abs(p.y - target) <= 0.14:
            p = replace(p, y=target)
        pinned.append(p)
    return pinned


def _fit_curve(logical, analysis, anchors, original_anchors, points):
    def adjusted(trace):
        out = trace.copy()
        indices = np.clip(
            np.searchsorted(anchors[:, 0], out[:, 0]) - 1, 0, len(anchors) - 2
        )
        t = np.clip(
            (out[:, 0] - anchors[indices, 0])
            / (anchors[indices + 1, 0] - anchors[indices, 0]),
            0,
            1,
        )
        blend = t * t * (3 - 2 * t)
        shifts = anchors[:, 1] - original_anchors[:, 1]
        out[:, 1] += shifts[indices] * (1 - blend) + shifts[indices + 1] * blend
        return out

    last_error = None
    candidate = None
    for smoothing in (0.025, 0.035, 0.05):
        fit_trace = analysis if smoothing == 0.025 else detect(logical, smoothing)[0]
        fit_trace = adjusted(fit_trace)
        for tolerance in (0.14, 0.2, 0.28, 0.08, 0.05, 0.1, 0.35):
            try:
                segments = primitive_bezier.fit(fit_trace, anchors, tolerance)
                incoming = segments[:-1, 3] - segments[:-1, 2]
                outgoing = segments[1:, 1] - segments[1:, 0]
                if len(incoming):
                    incoming /= np.linalg.norm(incoming, axis=1)[:, None]
                    outgoing /= np.linalg.norm(outgoing, axis=1)[:, None]
                    tangent_error = float(
                        np.max(np.linalg.norm(incoming - outgoing, axis=1))
                    )
                    if tangent_error > 1e-6:
                        raise UnsupportedCondition(
                            "a fitted curve join lost its tangent"
                        )
                else:
                    tangent_error = 0.0
                metrics = {"max_join_tangent_error": tangent_error}
                dense = _dense(segments)
                xs = np.linspace(dense[0, 0], dense[-1, 0], 3000)
                _, found = detect(
                    np.column_stack((xs, np.interp(xs, dense[:, 0], dense[:, 1]))),
                    0.005,
                )
                if [p.kind for p in found] != [p.kind for p in points]:
                    raise UnsupportedCondition(
                        "the fitted curve changed stationary points"
                    )
                error = float(
                    max(
                        max(cKDTree(dense).query(analysis)[0]),
                        max(cKDTree(analysis).query(dense)[0]),
                    )
                )
                if error > 0.25:
                    raise UnsupportedCondition(
                        "the fitted curve deviates from source ink by more than a quarter cell"
                    )
                metrics["fit_trace_smoothing_cells"] = smoothing
                candidate = segments, metrics, error
                break
            except ValueError as issue:
                last_error = issue
        if candidate is not None:
            break
    if candidate is None:
        raise last_error
    return candidate


def _recover_new(data, question):
    from . import raster_primitive

    image = Image.open(io.BytesIO(data)).convert("RGBA")
    if min(image.size) < 35 or max(image.size) > 5000:
        raise UnsupportedCondition("unsupported primitive raster dimensions")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    # Normalize only small source rasters; already large inputs retain their pixels.
    if min(image.size) < 400:
        background = background.resize(
            (image.width * 4, image.height * 4), Image.Resampling.LANCZOS
        )
    logical, grid, _, cleanup = primitive_trace.trace_source(
        np.asarray(background), question
    )
    analysis, points = detect(logical, 0.025)
    for smoothing in (0.02, 0.03):
        _, check = detect(logical, smoothing)
        if [p.kind for p in check] != [p.kind for p in points]:
            raise UnsupportedCondition(
                "the raster does not resolve a stable extremum count"
            )
    original_anchors = np.array(
        [logical[0], *[[p.x, p.y] for p in points], logical[-1]]
    )
    points = _pin_extrema(logical, points, question)
    anchors = np.array([logical[0], *[[p.x, p.y] for p in points], logical[-1]])

    segments, metrics, error = _fit_curve(
        logical, analysis, anchors, original_anchors, points
    )
    digest = hashlib.sha256(data).hexdigest()
    model = {
        "domain": [str(question.domain.lower), str(question.domain.upper)],
        "span": [str(question.interval.lower), str(question.interval.upper)],
        "knots": anchors.tolist(),
        "slopes": [0.0] * len(anchors),
        "bezier_segments": segments.tolist(),
        "extrema": [
            {
                "x": p.x,
                "y": p.y,
                "kind": "max" if p.kind == "maximum" else "min",
                "x_uncertainty": max(0.025, 3 / grid.vertical.step),
            }
            for p in points
        ],
        "source_sha256": digest,
        "diagnostics": {
            "method": "fitCurves-clean-ink-G1-v2",
            "source_cleanup": cleanup,
            "max_trace_error_cells": error,
            **metrics,
        },
    }
    verify(model)
    raster_primitive.select(model, question)
    return model
