"""Source annotation mask + full-span ink tracing; dedicated primitive runner."""

import math

import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

from solution_runner.converters import graph_png_to_svg_by_contrast as base

from .primitive_endpoints import locate_endpoints


def _grid_suppression(dark, grid):
    """Remove full measured grid/axis strokes, including anti-aliased edges."""
    result = base.grid_pixel_mask(dark.shape, grid).copy()
    foreground = dark > 0.05
    xlo, xhi = map(round, (min(grid.vertical.observed), max(grid.vertical.observed)))
    ylo, yhi = map(
        round, (min(grid.horizontal.observed), max(grid.horizontal.observed))
    )
    row_fraction = foreground[:, xlo : xhi + 1].mean(axis=1)
    column_fraction = foreground[ylo : yhi + 1, :].mean(axis=0)
    for y in [*grid.horizontal_lines(), grid.horizontal_axis_y]:
        rows = (abs(np.arange(dark.shape[0]) - y) < grid.horizontal.step * 0.12) & (
            row_fraction > 0.45
        )
        result[rows, :] = True
    for x in [*grid.vertical_lines(), grid.vertical_axis_x]:
        columns = (abs(np.arange(dark.shape[1]) - x) < grid.vertical.step * 0.12) & (
            column_fraction > 0.45
        )
        result[:, columns] = True
    return cv2.dilate(result.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)


def _full_path(dark, grid, lo, hi, endpoint_y=None):
    """Trace the whole stated domain without restarting on labels mid-graph."""
    left = round(grid.vertical_axis_x + lo * grid.vertical.step)
    right = round(grid.vertical_axis_x + hi * grid.vertical.step)
    dark.shape[0] - 1
    suppression = _grid_suppression(dark, grid)
    clean = dark.astype(np.float32).copy()
    clean[suppression] = 0
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


def trace_source(rgba, question):
    dark = base.effective_darkness(rgba)
    grid = base.detect_grid(
        dark,
        foreground_threshold=0.2,
        grid_mask_radius=None,
        vertical_axis_x=None,
        horizontal_axis_y=None,
    )
    clean = rgba.copy()
    bottom = round(min(grid.vertical.step, grid.horizontal.step) * 0.64)
    right = round(grid.vertical_axis_x + grid.vertical.step * 0.15)
    clean[:bottom, :right] = 255
    dark = base.effective_darkness(clean)
    lo, hi = float(question.domain.lower), float(question.domain.upper)
    rough = _full_path(dark, grid, lo, hi)
    # Recover the median ink around the full-span guide, then interpolate grid gaps.
    ink = dark > 0.35
    mask = ink & ~_grid_suppression(dark, grid)
    samples = _sample_curve(mask, rough, grid)
    if len(samples) < 30:
        raise ValueError("недостаточно различимого штриха кривой")
    if max(np.diff(samples[:, 0])) > grid.vertical.step * 0.65:
        raise ValueError("слишком большой разрыв в исходном штрихе")
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
    dark = base.effective_darkness(clean)
    mask = (dark > 0.35) & ~_grid_suppression(dark, grid)
    rough = _full_path(dark, grid, lo, hi, [p[1] for p in ends])
    samples = _sample_curve(mask, rough, grid)
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
    return logical, grid, clean, diagnostics
