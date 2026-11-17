"""Dedicated primitive-graph converter with explicit, preserved turning points."""

import hashlib
import io
import json
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator

from ...converters import graph_png_to_svg_by_contrast as base
from ...converters import graph_png_to_svg_by_extrema as extrema_reader
from ..probability.common import UnsupportedCondition
from . import graph_stationary, primitive_raster_render
from .primitive_metadata import META, NS

PNG = b"\x89PNG\r\n\x1a\n"


def _trace(rgba, question):
    dark, grid, trace = base.extract_graph(
        rgba,
        snap_tolerance_cells=0,
        smoothing_cells=0.01,
        simplify_cells=0.01,
        x_interval=base.XInterval(
            float(question.domain.lower), float(question.domain.upper), True, True
        ),
    )
    # Recover curve ink independently of the generic DP's grid bridges.
    yy, _xx = np.indices(dark.shape)
    mask = (
        (dark > 0.35)
        & (yy > min(trace.points[:, 1]) - grid.horizontal.step * 0.15)
        & (yy < max(trace.points[:, 1]) + grid.horizontal.step * 0.15)
    )
    ink = dark > 0.35
    xlo, xhi = map(round, (min(grid.vertical.observed), max(grid.vertical.observed)))
    ylo, yhi = map(
        round, (min(grid.horizontal.observed), max(grid.horizontal.observed))
    )
    row_coverage = ink[:, xlo : xhi + 1].mean(axis=1)
    column_coverage = ink[ylo : yhi + 1, :].mean(axis=0)
    for px in grid.vertical_lines():
        columns = np.flatnonzero(
            (abs(np.arange(dark.shape[1]) - px) < grid.vertical.step * 0.15)
            & (column_coverage > 0.45)
        )
        mask[:, columns] = False
    for py in grid.horizontal_lines():
        rows = np.flatnonzero(
            (abs(np.arange(dark.shape[0]) - py) < grid.horizontal.step * 0.15)
            & (row_coverage > 0.45)
        )
        mask[rows, :] = False
    samples = []
    for px in range(round(trace.start.pixel_x) + 1, round(trace.end.pixel_x)):
        ys = np.flatnonzero(mask[:, px])
        if not len(ys):
            continue
        groups = np.split(ys, np.flatnonzero(np.diff(ys) > 3) + 1)
        reference = np.interp(px, trace.points[:, 0], trace.points[:, 1])
        # The generic guide can jump onto a grid intersection beside a narrow
        # apex. Prefer continuation of the visible ink when that guide disagrees.
        predicted = reference
        if samples and px - samples[-1][0] <= grid.vertical.step * 0.15:
            predicted = samples[-1][1]
            if len(samples) >= 2:
                dx = samples[-1][0] - samples[-2][0]
                slope = (samples[-1][1] - samples[-2][1]) / dx
                predicted += np.clip(slope, -4, 4) * (px - samples[-1][0])
        center = min(
            (float(np.median(group)) for group in groups),
            key=lambda y: abs(y - reference) * 0.25 + abs(y - predicted) * 0.75,
        )
        if (
            abs(center - reference) <= grid.horizontal.step * 0.65
            or abs(center - predicted) <= grid.horizontal.step * 0.35
        ):
            samples.append([px, center])
    if len(samples) < 30:
        raise UnsupportedCondition("insufficient curve ink outside the coordinate grid")
    samples = np.array(
        [
            [trace.start.pixel_x, trace.start.pixel_y],
            *samples,
            [trace.end.pixel_x, trace.end.pixel_y],
        ]
    )
    if max(np.diff(samples[:, 0])) > grid.vertical.step * 0.65:
        raise UnsupportedCondition("the raster leaves an ambiguous gap in the curve")
    xs = trace.points[:, 0]
    ys = PchipInterpolator(samples[:, 0], samples[:, 1])(xs)
    logical = np.column_stack(
        (
            (xs - grid.vertical_axis_x) / grid.vertical.step,
            (grid.horizontal_axis_y - ys) / grid.horizontal.step,
        )
    )
    if (
        abs(logical[0, 0] - float(question.domain.lower)) > 0.1
        or abs(logical[-1, 0] - float(question.domain.upper)) > 0.1
    ):
        raise UnsupportedCondition("the visible curve does not cover the stated domain")
    return logical, grid


def _detect(logical, smooth, prominence):
    return extrema_reader.detect_extrema(
        logical,
        analysis_smoothing_cells=smooth,
        minimum_prominence_cells=prominence,
        minimum_separation_cells=0.12,
        refinement_window_cells=0.08,
        snap_tolerance_cells=-1,
    )


def select(model, question):
    from . import primitive_curves

    if primitive_curves.reviewed(model):
        return graph_stationary.select(
            [
                {"kind": p["kind"], "x": str(p["x"]), "svg": [p["x"], p["y"]]}
                for p in model["extrema"]
            ],
            question.interval,
        )
    points = []
    for index, point in enumerate(model["extrema"]):
        x = point["x"]
        neighbors = [
            abs(x - other["x"])
            for i, other in enumerate(model["extrema"])
            if i != index
        ]
        error = min(point["x_uncertainty"], min(neighbors, default=1) * 0.24)
        points.append(
            {
                "kind": point["kind"],
                "x_bounds": [str(x - error), str(x + error)],
                "svg": [x, point["y"]],
            }
        )
    return graph_stationary.select(points, question.interval)


def _verify_fit(knots, slopes, hard_indices):
    """Every derivative zero must be a recorded extremum, with no flat shelves."""
    if {
        i
        for i, slope in enumerate(slopes)
        if 0 < i < len(slopes) - 1 and abs(slope) < 1e-10
    } != set(hard_indices):
        raise UnsupportedCondition(
            "the fitted curve introduced an extra horizontal tangent"
        )
    for i in range(len(knots) - 1):
        dx = knots[i + 1, 0] - knots[i, 0]
        dy = (knots[i + 1, 1] - knots[i, 1]) / dx
        coefficients = [
            3 * (slopes[i] + slopes[i + 1] - 2 * dy),
            2 * (3 * dy - 2 * slopes[i] - slopes[i + 1]),
            slopes[i],
        ]
        if max(abs(value) for value in coefficients) < 1e-10:
            raise UnsupportedCondition("the fitted curve contains a horizontal segment")
        roots = np.roots(np.trim_zeros(coefficients, "f"))
        if any(abs(root.imag) < 1e-7 and 1e-6 < root.real < 1 - 1e-6 for root in roots):
            raise UnsupportedCondition(
                "the fitted branch has an unrecorded stationary point"
            )


def _smooth_vertices(knots, slopes, hard_indices, width=0.5):
    """Round only neighborhoods of extrema, retaining their exact coordinates.

    Splice tangents and every curve segment outside these neighborhoods stay
    unchanged. The first and last SVG segments are always retained verbatim.
    """
    keep = np.ones(len(knots), dtype=bool)
    regions = []
    for position, index in enumerate(hard_indices):
        previous = hard_indices[position - 1] if position else 0
        following = (
            hard_indices[position + 1]
            if position + 1 < len(hard_indices)
            else len(knots) - 1
        )
        left = right = index
        for direction in (-1, 1):
            neighbor = previous if direction < 0 else following
            radius = min(width, abs(knots[index, 0] - knots[neighbor, 0]) * 0.49)
            candidates = (
                range(max(1, previous + 1), index)
                if direction < 0
                else range(min(len(knots) - 2, following - 1), index, -1)
            )
            for candidate in candidates:
                if abs(knots[candidate, 0] - knots[index, 0]) > radius:
                    continue
                a, b = sorted((candidate, index))
                delta = (knots[b, 1] - knots[a, 1]) / (knots[b, 0] - knots[a, 0])
                if abs(delta) < 1e-10 or not 0 <= slopes[candidate] / delta <= 3:
                    continue
                xs = np.linspace(knots[a, 0], knots[b, 0], 41)
                before = extrema_reader._evaluate_hermite(knots, slopes, xs)
                after = extrema_reader._evaluate_hermite(
                    knots[[a, b]], slopes[[a, b]], xs
                )
                if max(abs(before - after)) > 0.25:
                    continue
                if direction < 0:
                    left = candidate
                else:
                    right = candidate
                break
        keep[left + 1 : index] = False
        keep[index + 1 : right] = False
        regions.append([float(knots[left, 0]), float(knots[right, 0])])
    retained = np.flatnonzero(keep).tolist()
    new_knots = knots[keep].copy()
    new_slopes = slopes[keep].copy()
    new_hard = tuple(retained.index(index) for index in hard_indices)
    _verify_fit(new_knots, new_slopes, new_hard)
    return (
        new_knots,
        new_slopes,
        {"width_cells": width, "regions": regions, "removed_knots": int((~keep).sum())},
    )


def _recover_legacy(data, question, *, smooth_vertices=True):
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    if min(image.size) < 35 or max(image.size) > 5000:
        raise UnsupportedCondition("unsupported primitive raster dimensions")
    background = Image.new("RGBA", image.size, "white")
    background.alpha_composite(image)
    logical, grid = _trace(np.asarray(background), question)
    analysis, points = _detect(logical, 0.025, 0.08)
    # Changing raster-scale smoothing must not change the requested count.
    main = [
        p
        for p in points
        if float(question.interval.lower) <= p.x <= float(question.interval.upper)
    ]
    for smooth, prominence in ((0.02, 0.06), (0.03, 0.10)):
        _, other = _detect(logical, smooth, prominence)
        selected = [
            p
            for p in other
            if float(question.interval.lower) <= p.x <= float(question.interval.upper)
        ]
        if len(selected) != len(main) or [p.kind for p in selected] != [
            p.kind for p in main
        ]:
            raise UnsupportedCondition(
                "the raster does not resolve a stable extremum count"
            )
    fit = extrema_reader.fit_logical_curve(
        analysis,
        points,
        maximum_error_cells=0.045,
        minimum_support_spacing_cells=0.035,
        # The shared fitter enforces 0.12-cell relief at shoulders. Putting
        # those supports only 0.065 cells from the apex creates artificial
        # steep caps followed by shelves after monotonic projection.
        extremum_shoulder_cells=0.15,
        slope_smoothing=0,
        extremum_rounding=0.08,
        maximum_knots=300,
    )
    if len(fit.extrema) != len(points) or fit.maximum_trace_residual > 0.3:
        raise UnsupportedCondition(
            "the SVG cannot preserve the source extrema within tolerance"
        )
    hard = fit.logical_knots[
        [0, *fit.extremum_knot_indices, len(fit.logical_knots) - 1]
    ]
    knots = extrema_reader._project_between_extrema(fit.logical_knots, hard)
    slopes = extrema_reader._pchip_slopes_with_extrema(
        knots, fit.extremum_knot_indices, smoothing=0, extremum_rounding=0.08
    )
    _verify_fit(knots, slopes, fit.extremum_knot_indices)
    vertex_smoothing = None
    if smooth_vertices:
        knots, slopes, vertex_smoothing = _smooth_vertices(
            knots, slopes, fit.extremum_knot_indices
        )
    return {
        "domain": [str(question.domain.lower), str(question.domain.upper)],
        "span": [str(question.interval.lower), str(question.interval.upper)],
        "knots": knots.tolist(),
        "slopes": slopes.tolist(),
        "extrema": [
            {
                "x": p.x,
                "y": p.y,
                "kind": "max" if p.kind == "maximum" else "min",
                "x_uncertainty": max(0.05, 3 / grid.vertical.step),
            }
            for p in fit.extrema
        ],
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "diagnostics": {
            "max_trace_error_cells": fit.maximum_trace_residual,
            "vertex_smoothing": vertex_smoothing,
            "source_units": [grid.vertical.step, grid.horizontal.step],
            "source_origin": [grid.vertical_axis_x, grid.horizontal_axis_y],
        },
    }


def recover(data, question, *, smooth_vertices=True):
    from . import primitive_curves

    return primitive_curves.recover(data, question)


render = primitive_raster_render.render


def embedded(data, question):
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    node = root.find(NS + 'metadata[@id="' + META + '"]')
    if node is None:
        return None
    payload = json.loads(node.text)
    model = payload["model"]
    if payload["highlighted"] or render(model).encode() != data:
        raise UnsupportedCondition("the prepared primitive SVG changed")
    if model["domain"] != [
        str(question.domain.lower),
        str(question.domain.upper),
    ] or model["span"] != [str(question.interval.lower), str(question.interval.upper)]:
        raise UnsupportedCondition("the primitive SVG and stated intervals disagree")
    return model
