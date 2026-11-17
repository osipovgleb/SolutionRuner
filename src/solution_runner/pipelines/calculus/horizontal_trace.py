"""Scoped horizontal-tangent trace with the larger endpoint rings of this family."""

import math
from itertools import pairwise

import cv2
import numpy as np
from scipy.interpolate import PchipInterpolator

from solution_runner.converters import graph_png_to_svg_by_contrast as base


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
    # These source rasters place y=f(x) above the top grid line. Mask that
    # entire header, including glyph descenders; a fixed strip left half of f.
    bottom = max(
        round(min(grid.vertical.step, grid.horizontal.step) * 0.64),
        round(min(grid.horizontal.observed)),
    )
    right = clean.shape[1]
    clean[:bottom, :right] = 255
    dark = base.effective_darkness(clean)
    lo, hi = float(question.domain.lower), float(question.domain.upper)
    rough = _full_path(dark, grid, lo, hi)
    # Recover the median ink around the full-span guide, then interpolate grid gaps.
    ink = dark > 0.35
    mask = ink & ~_grid_suppression(dark, grid)
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
    if len(samples) < 30:
        raise ValueError("недостаточно различимого штриха кривой")
    samples = np.array(samples)
    for a, b in pairwise(samples):
        if b[0] - a[0] <= grid.vertical.step * 0.65:
            continue
        # A shallow cap may overlap a horizontal grid stroke for nearly a
        # whole cell. Bridge only such measured grid occlusions, not arbitrary
        # missing branches. The later shape/turn/deviation checks still apply.
        line_y = min(grid.horizontal_lines(), key=lambda y: abs(y - (a[1] + b[1]) / 2))
        if (
            b[0] - a[0] > grid.vertical.step * 1.3
            or max(abs(a[1] - line_y), abs(b[1] - line_y)) > grid.horizontal.step * 0.22
        ):
            raise ValueError("слишком большой разрыв в исходном штрихе")
    # Match the open-circle pattern at the exact domain boundary. Unlike
    # contour/Hough candidates, this does not mistake a nearby coordinate digit
    # for the marker simply because that digit has a partial round contour.
    marker_dark = base.effective_darkness(clean)
    step = min(grid.vertical.step, grid.horizontal.step)
    response = np.full(marker_dark.shape, -1.0, dtype=np.float32)
    radius_map = np.zeros(marker_dark.shape, dtype=np.float32)
    for radius in np.linspace(step * 0.035, step * 0.14, 16):
        half = int(np.ceil(radius + 3))
        yy, xx = np.mgrid[-half : half + 1, -half : half + 1]
        rr = np.sqrt(xx * xx + yy * yy)
        ring = np.exp(-0.5 * ((rr - radius) / max(1.0, step * 0.009)) ** 2)
        ring /= ring.sum()
        center = np.exp(-0.5 * (rr / max(1.0, radius * 0.3)) ** 2)
        center /= center.sum()
        value = cv2.filter2D(marker_dark, -1, ring - 1.15 * center)
        take = value > response
        response[take] = value[take]
        radius_map[take] = radius
    diagnostics = {
        "header_mask": [0, 0, right, bottom],
        "markers": [],
        "grid": {
            "x0": grid.vertical_axis_x,
            "y0": grid.horizontal_axis_y,
            "sx": grid.vertical.step,
            "sy": grid.horizontal.step,
        },
    }
    ends = []
    for side, bound in enumerate((lo, hi)):
        expected = grid.vertical_axis_x + bound * grid.vertical.step
        center_x = min(grid.vertical.observed, key=lambda x: abs(x - expected))
        xlo = max(0, round(center_x - step * 0.015))
        xhi = min(response.shape[1], round(center_x + step * 0.015) + 1)
        band = response[:, xlo:xhi].copy()
        # Penalize circles that belong to text instead of the graph. The
        # full-span trace is used only as a weak tie breaker, never as an anchor.
        dist = rough[:, 0] - expected if side == 0 else expected - rough[:, 0]
        points = rough[(dist > step * 0.3) & (dist < step * 0.6)]
        forecast = float(
            np.polyval(np.polyfit(points[:, 0] - expected, points[:, 1], 1), 0)
        )
        band -= 0.15 * np.abs(np.arange(response.shape[0])[:, None] - forecast) / step
        best = None
        best_score = -1e12
        for flat in np.argsort(band.ravel())[-240:][::-1]:
            iy, ix = np.unravel_index(flat, band.shape)
            x = int(xlo + ix)
            radius = float(radius_map[iy, x])
            ang = np.linspace(0, 2 * np.pi, 48, endpoint=False)
            rings = []
            for rr in (radius - 1, radius, radius + 1):
                ax = (
                    np.rint(x + rr * np.cos(ang))
                    .astype(int)
                    .clip(0, marker_dark.shape[1] - 1)
                )
                ay = (
                    np.rint(iy + rr * np.sin(ang))
                    .astype(int)
                    .clip(0, marker_dark.shape[0] - 1)
                )
                rings.append(marker_dark[ay, ax])
            coverage = float(np.mean(np.max(rings, axis=0) > 0.2))
            if coverage < 0.82:
                continue
            candidate = (x, float(iy), radius, float(response[iy, x]), coverage)
            if coverage >= 0.94:
                best = candidate
                break
            score = float(band[iy, ix]) + 0.15 * coverage
            if score > best_score:
                best = candidate
                best_score = score
        if best is None:
            raise ValueError("не удалось уверенно распознать кружок на конце графика")
        x, y, radius, quality, coverage = best
        if quality < 0.045:
            raise ValueError("не удалось уверенно распознать кружок на конце графика")
        ends.append([expected, y])
        diagnostics["markers"].append(
            {
                "x": x,
                "y": y,
                "radius": radius,
                "quality": quality,
                "ring_coverage": coverage,
                "forecast_y": forecast,
            }
        )
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
    samples = _bridge_grid_caps(np.array(samples), grid)
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
