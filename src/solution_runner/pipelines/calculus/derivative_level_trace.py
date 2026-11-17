"""Scoped horizontal-tangent trace with the larger endpoint rings of this family."""

import math
from itertools import pairwise

import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

from solution_runner.converters import graph_png_to_svg_by_contrast as base

from .derivative_level_endpoints import locate_endpoints


def _grid_suppression(dark, grid):
    """Erase measured stroke cores, preserving darker curve crossings."""
    result = np.zeros(dark.shape, dtype=bool)
    xlo, xhi = map(round, (min(grid.vertical.observed), max(grid.vertical.observed)))
    ylo, yhi = map(
        round, (min(grid.horizontal.observed), max(grid.horizontal.observed))
    )
    row_profile = np.quantile(dark[:, xlo : xhi + 1], 0.65, axis=1)
    column_profile = np.quantile(dark[ylo : yhi + 1, :], 0.65, axis=0)
    for center, step, profile, vertical in [
        *[
            (y, grid.horizontal.step, row_profile, False)
            for y in [*grid.horizontal_lines(), grid.horizontal_axis_y]
        ],
        *[
            (x, grid.vertical.step, column_profile, True)
            for x in [*grid.vertical_lines(), grid.vertical_axis_x]
        ],
    ]:
        near = abs(np.arange(len(profile)) - center) <= max(2, step * 0.08)
        peak = float(profile[near].max())
        core = near & (profile >= max(0.035, peak * 0.5))
        if vertical:
            result[:, core] |= dark[:, core] <= profile[core][None, :] + 0.18
        else:
            result[core, :] |= dark[core, :] <= profile[core][:, None] + 0.18
    return result


def clean_curve_ink(dark, grid, endpoints=()):
    """Remove measured grid strokes, then small disconnected text glyphs."""
    mask = (dark > 0.35) & ~_grid_suppression(dark, grid)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), 8)
    keep = np.zeros(count, dtype=bool)
    step = min(grid.vertical.step, grid.horizontal.step)
    for label in range(1, count):
        x, y, width, height, area = stats[label]
        # A curve fragment between two grid strokes spans almost a cell.
        # Digits and formula glyphs form much shorter disconnected islands.
        label_zone = (
            abs(x + width / 2 - grid.vertical_axis_x) < step * 0.85
            or abs(y + height / 2 - grid.horizontal_axis_y) < step * 0.85
        )
        keep[label] = (
            not label_zone
            or max(width, height) >= step * 0.55
            or any(
                abs(x + width / 2 - ex) < step * 0.65
                and abs(y + height / 2 - ey) < step * 0.25
                for ex, ey in endpoints
            )
        )
        if area <= max(3, step * 0.1) and max(width, height) <= step * 0.1:
            keep[label] = False
    return keep[labels]


def _full_path(dark, grid, lo, hi, endpoint_y=None):
    """Trace the whole stated domain without restarting on labels mid-graph."""
    left = round(grid.vertical_axis_x + lo * grid.vertical.step)
    right = round(grid.vertical_axis_x + hi * grid.vertical.step)
    dark.shape[0] - 1
    clean = dark.astype(np.float32).copy()
    endpoints = (
        () if endpoint_y is None else ((left, endpoint_y[0]), (right, endpoint_y[1]))
    )
    clean[~clean_curve_ink(dark, grid, endpoints)] = 0
    signal = cv2.GaussianBlur(
        clean,
        (0, 0),
        sigmaX=max(0.6, grid.vertical.step * 0.009),
        sigmaY=max(0.6, grid.horizontal.step * 0.009),
    )
    evidence = 4.5 * signal[:, left : right + 1] - 0.12
    height, width = evidence.shape
    previous = evidence[:, 0].copy()
    if endpoint_y is not None:
        previous -= 0.5 * (np.arange(height) - endpoint_y[0]) ** 2
    back = np.zeros((width, height), dtype=np.int16)
    maximum = min(96, max(8, math.ceil(grid.horizontal.step * 0.6)))
    scale = 28 / grid.horizontal.step
    for i in range(1, width):
        best = np.full(height, -1e12, dtype=np.float32)
        deltas = np.zeros(height, dtype=np.int16)
        for delta in range(-maximum, maximum + 1):
            shifted = base._shifted(previous, delta, -1e12)
            candidate = shifted - (
                0.012 * abs(delta) * scale + 0.002 * delta * delta * scale * scale
            )
            take = candidate > best
            best[take] = candidate[take]
            deltas[take] = delta
        previous = best + evidence[:, i]
        back[i] = deltas
    if endpoint_y is not None:
        previous -= 0.5 * (np.arange(height) - endpoint_y[1]) ** 2
    y = int(np.argmax(previous))
    ys = np.empty(width)
    ys[-1] = y
    for i in range(width - 1, 0, -1):
        y -= int(back[i, y])
        ys[i - 1] = y
    return np.column_stack((np.arange(left, right + 1), ys))


def _bridge_grid_caps(samples, grid):
    """Recover one rounded cap hidden under a measured horizontal grid stroke."""
    result = [samples[0]]
    for i, (a, b) in enumerate(pairwise(samples)):
        gap = b[0] - a[0]
        if grid.vertical.step * 0.65 < gap <= grid.vertical.step * 1.3:
            line_y = min(
                grid.horizontal_lines(), key=lambda y: abs(y - (a[1] + b[1]) / 2)
            )
            left = a[1] - line_y
            right = b[1] - line_y
            if (
                left * right > 0
                and max(abs(left), abs(right)) <= grid.horizontal.step * 0.22
            ):
                prior = samples[max(0, i - 3)]
                following = samples[min(len(samples) - 1, i + 4)]
                side = np.sign(left)
                if (a[1] - prior[1]) * side <= 0 and (following[1] - b[1]) * side >= 0:
                    center = (a[0] + b[0]) / 2
                    for x in np.linspace(a[0], b[0], max(5, int(gap / 2)))[1:-1]:
                        end = a if x <= center else b
                        y = (
                            line_y
                            + (end[1] - line_y)
                            * ((x - center) / (end[0] - center)) ** 2
                        )
                        result.append([x, y])
        result.append(b)
    return np.array(result)


def _sample_curve(mask, rough, grid):
    samples = []
    for px, reference in rough:
        px = int(px)
        ys = np.flatnonzero(mask[:, px])
        if not len(ys):
            continue
        groups = np.split(ys, np.flatnonzero(np.diff(ys) > 3) + 1)
        center = min(
            (float(np.median(g)) for g in groups), key=lambda y: abs(y - reference)
        )
        if abs(center - reference) < grid.horizontal.step * 0.25:
            samples.append([px, center])
    return np.array(samples)


def _prepare_source(rgba, dark, grid, question):
    clean = rgba.copy()
    # Older coloured diagrams have black formula labels inside the plot.
    # Keep coloured curve ink, while removing achromatic text away from the
    # coordinate axes and the two endpoint markers.
    rgb = rgba[:, :, :3].astype(float)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    coloured_ink = (chroma > 30) & (rgb.mean(axis=2) < 190)
    if coloured_ink.sum() > rgba.shape[0] * rgba.shape[1] * 0.001:
        yy, xx = np.indices(dark.shape)
        left = grid.vertical_axis_x + float(question.domain.lower) * grid.vertical.step
        right = grid.vertical_axis_x + float(question.domain.upper) * grid.vertical.step
        protected = (abs(xx - left) < grid.vertical.step * 0.25) | (
            abs(xx - right) < grid.vertical.step * 0.25
        )
        protected |= (abs(xx - grid.vertical_axis_x) < grid.vertical.step * 0.12) | (
            abs(yy - grid.horizontal_axis_y) < grid.horizontal.step * 0.12
        )
        clean[(chroma < 18) & (dark > 0.18) & ~protected] = 255

    # These source rasters place y=f(x) above the top grid line. Mask that
    # entire header, including glyph descenders; a fixed strip left half of f.
    bottom = max(
        round(min(grid.vertical.step, grid.horizontal.step) * 0.64),
        round(min(grid.horizontal.observed)),
    )
    if min(grid.horizontal.observed) < grid.horizontal.step * 0.15:
        bottom = 0
    right = clean.shape[1]
    clean[:bottom, :right] = 255
    return clean, chroma, coloured_ink, (right, bottom)


def trace_source(rgba, question):
    dark = base.effective_darkness(rgba)
    grid = base.detect_grid(
        dark,
        foreground_threshold=0.06,
        grid_mask_radius=None,
        vertical_axis_x=None,
        horizontal_axis_y=None,
    )
    clean, chroma, coloured_ink, (right, bottom) = _prepare_source(
        rgba, dark, grid, question
    )
    dark = base.effective_darkness(clean)
    lo, hi = float(question.domain.lower), float(question.domain.upper)
    rough = _full_path(dark, grid, lo, hi)
    # Recover the median ink around the full-span guide, then interpolate grid gaps.
    mask = clean_curve_ink(dark, grid)
    samples = _sample_curve(mask, rough, grid)
    if len(samples) < 30:
        raise ValueError("недостаточно различимого штриха кривой")
    # Match the open-circle pattern at the exact domain boundary. Unlike
    # contour/Hough candidates, this does not mistake a nearby coordinate digit
    # for the marker simply because that digit has a partial round contour.
    ends, markers = locate_endpoints(clean, grid, rough, (lo, hi))
    step = min(grid.vertical.step, grid.horizontal.step)
    diagnostics = {
        "header_mask": [0, 0, right, bottom],
        "markers": markers,
        "grid": {
            "x0": grid.vertical_axis_x,
            "y0": grid.horizontal_axis_y,
            "sx": grid.vertical.step,
            "sy": grid.horizontal.step,
        },
    }
    # Coordinate labels occupy the opposite side of the axis to the endpoint.
    # Clear their source-specific margin boxes before tracing, leaving the
    # endpoint marker and the curve side intact.
    diagnostics["coordinate_masks"] = []
    for x, y in ends:
        xa = max(0, round(x - step * 0.23))
        xb = min(clean.shape[1], round(x + step * 0.23))
        if y < grid.horizontal_axis_y:
            ya = round(grid.horizontal_axis_y + step * 0.08)
            yb = round(grid.horizontal_axis_y + step * 0.65)
        else:
            ya = round(grid.horizontal_axis_y - step * 0.65)
            yb = round(grid.horizontal_axis_y - step * 0.08)
        ya = max(0, ya)
        yb = min(clean.shape[0], yb)
        clean[ya:yb, xa:xb] = 255
        diagnostics["coordinate_masks"].append([xa, ya, xb, yb])
    if coloured_ink.sum() > rgba.shape[0] * rgba.shape[1] * 0.001:
        yy, xx = np.indices(dark.shape)
        protected = (abs(xx - grid.vertical_axis_x) < grid.vertical.step * 0.12) | (
            abs(yy - grid.horizontal_axis_y) < grid.horizontal.step * 0.12
        )
        for x, y in ends:
            protected |= ((xx - x) ** 2 + (yy - y) ** 2) < (step * 0.2) ** 2
        clean[(chroma < 18) & (base.effective_darkness(clean) > 0.18) & ~protected] = (
            255
        )
    dark = base.effective_darkness(clean)
    mask = clean_curve_ink(dark, grid, ends)
    rough = _full_path(dark, grid, lo, hi, [p[1] for p in ends])
    samples = _sample_curve(mask, rough, grid)
    samples = _bridge_grid_caps(samples, grid)
    interior = samples[
        (samples[:, 0] > ends[0][0] + grid.vertical.step * 0.11)
        & (samples[:, 0] < ends[1][0] - grid.vertical.step * 0.11)
    ]
    support = np.vstack((ends[0], interior, ends[1]))
    xs = np.linspace(ends[0][0], ends[1][0], len(rough))
    ys = PchipInterpolator(support[:, 0], support[:, 1])(xs)
    logical = np.column_stack(
        (
            (xs - grid.vertical_axis_x) / grid.vertical.step,
            (grid.horizontal_axis_y - ys) / grid.horizontal.step,
        )
    )
    diagnostics["clean_ink_components"] = True
    curve_only = np.full_like(clean, 255)
    curve_only[mask] = clean[mask]
    diagnostics["endpoints"] = [list(p) for p in ends]
    return logical, grid, curve_only, diagnostics
