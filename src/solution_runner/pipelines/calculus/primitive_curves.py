"""Fit source primitive curves, retaining fixed extrema and smooth G2 joins."""

import hashlib
import io
import itertools
import json
from copy import deepcopy
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

from ..probability.common import UnsupportedCondition
from . import primitive_bezier, primitive_trace

APPROVED = Path(__file__).with_name("assets") / "primitive-reviewed-curves.json"


def reviewed(model):
    if not APPROVED.exists():
        return False
    approved = json.loads(APPROVED.read_text()).get(model.get("source_sha256"))
    return approved is not None and approved == model


def detect(logical, smooth):
    from . import raster_primitive

    analysis, points = raster_primitive._detect(logical, smooth, 0.04)
    points = list(points)
    while True:
        pairs = [
            (abs(b.y - a.y), i)
            for i, (a, b) in enumerate(itertools.pairwise(points))
            if a.kind != b.kind and b.x - a.x < 0.15 and abs(b.y - a.y) < 0.12
        ]
        if not pairs:
            break
        _, i = min(pairs)
        del points[i : i + 2]
    result = []
    for point in points:
        if result and result[-1].kind == point.kind:
            old = result[-1]
            if point.y > old.y if point.kind == "maximum" else point.y < old.y:
                result[-1] = point
        else:
            result.append(point)
    return analysis, result


def _dense(segments):
    t = np.linspace(0, 1, 151, endpoint=False)[:, None]
    return np.vstack(
        [
            *[
                (1 - t) ** 3 * s[0]
                + 3 * (1 - t) ** 2 * t * s[1]
                + 3 * (1 - t) * t * t * s[2]
                + t**3 * s[3]
                for s in segments
            ],
            segments[-1, -1],
        ]
    )


def recover(data, question):
    digest = hashlib.sha256(data).hexdigest()
    if APPROVED.exists():
        approved = json.loads(APPROVED.read_text()).get(digest)
        if approved:
            model = deepcopy(approved)
            if model["domain"] != [
                str(question.domain.lower),
                str(question.domain.upper),
            ] or model["span"] != [
                str(question.interval.lower),
                str(question.interval.upper),
            ]:
                raise UnsupportedCondition(
                    "the reviewed primitive and stated intervals disagree"
                )
            verify(model)
            return model
    try:
        return _recover_new(data, question, digest)
    except (ValueError, AssertionError) as error:
        raise UnsupportedCondition(
            str(error) or "the source curve could not be verified"
        ) from error


def _recover_new(data, question, digest):
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
    for tolerance in (0.14, 0.2, 0.28, 0.08):
        try:
            segments, metrics = primitive_bezier.harmonize(
                primitive_bezier.fit(analysis, anchors, tolerance)
            )
            break
        except ValueError as error:
            last_error = error
    else:
        raise last_error
    dense = _dense(segments)
    xs = np.linspace(dense[0, 0], dense[-1, 0], 3000)
    _, found = detect(
        np.column_stack((xs, np.interp(xs, dense[:, 0], dense[:, 1]))), 0.005
    )
    if [p.kind for p in found] != [p.kind for p in points]:
        raise UnsupportedCondition("the fitted curve changed stationary points")
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


def verify(model):
    segments = np.array(model["bezier_segments"])
    primitive_bezier.verify(segments)
    for point in model["extrema"]:
        xy = np.array([point["x"], point["y"]])
        ids = [i for i, s in enumerate(segments) if np.array_equal(s[3], xy)]
        if len(ids) != 1 or ids[0] >= len(segments) - 1:
            raise UnsupportedCondition("an extremum is not a fixed curve join")
        i = ids[0]
        if (
            abs(segments[i, 2, 1] - xy[1]) > 1e-10
            or abs(segments[i + 1, 1, 1] - xy[1]) > 1e-10
        ):
            raise UnsupportedCondition("a fixed extremum lost its horizontal tangent")
