"""Fit horizontal-tangent graphs using the established constrained curve fitter."""

import hashlib
import io
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from ..probability.common import UnsupportedCondition
from . import horizontal_bezier, primitive_bezier
from . import horizontal_trace as primitive_trace
from .primitive_curves import _dense, detect, verify

VERIFIED_CURVES = Path(__file__).with_name("assets") / "horizontal-verified-curves.json"
TRACE_VERSION = "horizontal-trace-v2"


def recover(data, question):
    """Reuse a verified reconstruction only for the exact original PNG bytes."""
    digest = hashlib.sha256(data).hexdigest()
    if VERIFIED_CURVES.exists():
        cache = json.loads(VERIFIED_CURVES.read_text())
        if cache.get("trace_version") == TRACE_VERSION:
            stored = cache.get("models", {}).get(digest)
            if stored is not None:
                model = deepcopy(stored)
                if (
                    model["source_sha256"] != digest
                    or model["domain"]
                    != [str(question.domain.lower), str(question.domain.upper)]
                    or model["span"]
                    != [str(question.interval.lower), str(question.interval.upper)]
                ):
                    raise UnsupportedCondition(
                        "the verified reconstruction and current question disagree"
                    )
                verify(model)
                return model
    return _recover_new(data, question)


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
    anchors = np.array([logical[0], *[[p.x, p.y] for p in points], logical[-1]])
    last_error = None
    candidate = None
    for smoothing in (0.025, 0.035, 0.05):
        fit_trace = analysis if smoothing == 0.025 else detect(logical, smoothing)[0]
        for tolerance in (0.14, 0.2, 0.28, 0.08):
            try:
                segments, metrics = horizontal_bezier.harmonize(
                    primitive_bezier.fit(fit_trace, anchors, tolerance)
                )
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
    segments, metrics, error = candidate
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
            "method": "fitCurves-G2-v1",
            "source_cleanup": cleanup,
            "max_trace_error_cells": error,
            **metrics,
        },
    }
    verify(model)
    raster_primitive.select(model, question)
    return model
