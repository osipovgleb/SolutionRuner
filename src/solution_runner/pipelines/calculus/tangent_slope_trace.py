"""Scoped raster recovery for a function with one marked straight tangent."""

import io
import logging
import math
from dataclasses import replace
from fractions import Fraction
from xml.etree import ElementTree as ET

import cv2
import numpy as np
from PIL import Image

from solution_runner.converters import graph_png_to_svg_by_contrast as base

from .derivative_level_trace import clean_curve_ink


def _guide(dark, grid, tangent):
    try:
        return base.detect_vertical_tangency_guide(dark, grid, tangent)
    except ValueError as exc:
        logging.getLogger(__name__).debug(
            "Primary tangent guide detection failed: %s", exc
        )
    # Some x₀ guides are closer than .22 cell to a grid line. Inspect actual
    # dash support between the axis and tangent, excluding measured grid cores.
    step = min(grid.vertical.step, grid.horizontal.step)
    candidates = []
    for x in range(2, dark.shape[1] - 2):
        if min(abs(x - gx) for gx in grid.vertical_lines()) < max(1.5, step * 0.08):
            continue
        end = tangent.y_at(x)
        lo, hi = sorted((round(grid.horizontal_axis_y), round(end)))
        lo, hi = max(0, lo), min(dark.shape[0] - 1, hi)
        if hi - lo < step * 0.7:
            continue
        ys = np.arange(lo + 2, hi - 1)
        usable = np.array(
            [min(abs(y - gy) for gy in grid.horizontal_lines()) > 1.4 for y in ys]
        )
        ink = dark[ys, x] > 0.5
        support = ink[usable]
        if len(support) < 6 or not 0.2 <= support.mean() <= 0.85:
            continue
        # A true dashed guide has several separate runs along its length.
        runs = np.count_nonzero(np.diff(np.r_[False, ink, False].astype(int)) == 1)
        if runs >= 3:
            candidates.append((float(support.sum()), x))
    if not candidates:
        raise ValueError("the dashed tangency guide could not be isolated")
    _, x = max(candidates)
    return base.VerticalGuide(float(x), grid.horizontal_axis_y, tangent.y_at(x))


def _curve(dark, grid, tangent, guide):
    step = min(grid.vertical.step, grid.horizontal.step)
    yy, xx = np.indices(dark.shape)
    distance = (
        abs(tangent.slope * xx - yy + tangent.intercept) / (1 + tangent.slope**2) ** 0.5
    )
    ink = clean_curve_ink(dark, grid)
    # Remove just the measured straight stroke, retaining the touching curve.
    ink &= ~(
        (distance < max(1.1, step * 0.09)) & (abs(xx - guide.pixel_x) > step * 0.65)
    )
    ink &= ~(
        (abs(xx - guide.pixel_x) < 1.3)
        & (yy >= min(guide.start_y, guide.end_y))
        & (yy <= max(guide.start_y, guide.end_y))
        & (abs(yy - guide.end_y) > 2)
    )
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink.astype("uint8"), 8)
    keep = np.zeros(count, dtype=bool)
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        keep[i] = area >= 3 and max(w, h) >= step * 0.45
        near_axis = (
            abs(x + w / 2 - grid.vertical_axis_x) < step * 0.9
            or abs(y + h / 2 - grid.horizontal_axis_y) < step * 0.9
        )
        if near_axis and max(w, h) < step * 0.8:
            keep[i] = False
    clean = np.where(keep[labels], dark, 0).astype("float32")
    blurred = cv2.GaussianBlur(clean, (0, 0), sigmaX=0.6, sigmaY=0.6)
    evidence = 4.5 * blurred - 0.30
    left, ls = base._anchored_curve_direction(
        evidence,
        grid,
        anchor_x=round(guide.pixel_x),
        anchor_y=round(guide.end_y),
        direction=-1,
    )
    right, rs = base._anchored_curve_direction(
        evidence,
        grid,
        anchor_x=round(guide.pixel_x),
        anchor_y=round(guide.end_y),
        direction=1,
    )
    raw = np.vstack([left, right[1:]])
    return raw, ls + rs


def extract(data):
    rgba = np.asarray(Image.open(io.BytesIO(data)).convert("RGBA"))
    dark = base.effective_darkness(rgba)
    try:
        grid = base.detect_grid(
            dark,
            foreground_threshold=0.2,
            grid_mask_radius=None,
            vertical_axis_x=None,
            horizontal_axis_y=None,
        )
    except ValueError:
        grid = base.detect_grid(
            dark,
            foreground_threshold=0.6,
            grid_mask_radius=None,
            vertical_axis_x=None,
            horizontal_axis_y=None,
        )
    tangent = base.detect_tangent_line(dark, grid)
    k = Fraction(tangent.logical_slope).limit_denominator(10)
    if abs(float(k) - tangent.logical_slope) > 0.015:
        raise ValueError("the tangent slope does not resolve to the source lattice")
    guide = _guide(dark, grid, tangent)
    markers = base.detect_marked_tangent_grid_points(dark, grid, tangent, guide)
    raw, score = _curve(dark, grid, tangent, guide)
    points, start, end = base.snap_curve_endpoints(
        raw, grid, snap_tolerance_cells=0.22, snap_y_to_grid=False
    )
    smooth, simple = base.smooth_and_simplify_curve(
        points, grid, smoothing_cells=0.075, simplify_cells=0.05
    )
    smooth, simple = base.enforce_tangent_contact(
        smooth, grid, tangent, guide, simplify_cells=0.05
    )
    trace = base.TraceResult(
        raw, smooth, simple, score, start, end, tangent, guide, markers
    )
    # Some source curves continue into a partial bottom grid cell. Include that
    # cell in the SVG frame rather than clipping a real minimum at its border.
    if float(smooth[:, 1].max()) > grid.horizontal_lines()[-1]:
        last = (
            grid.horizontal.origin
            + math.ceil(
                (float(smooth[:, 1].max()) - grid.horizontal.origin)
                / grid.horizontal.step
            )
            * grid.horizontal.step
        )
        grid = replace(grid, image_height=math.ceil(last) + 1)
    svg = base.render_graph_with_tangent_svg(
        grid,
        trace,
        cell_size=20,
        pad_cells=0,
        path_mode="bezier",
        bezier_error_cells=0.05,
        endpoint_style="none",
        include_labels=True,
        curve_color="#143B8F",
        graph_label="y = f(x)",
    )
    svg = svg.replace("x₀", 'x<tspan baseline-shift="sub" font-size="8">0</tspan>')
    origin = [
        (grid.vertical_axis_x - grid.vertical_lines()[0]) / grid.vertical.step * 20,
        (grid.horizontal_axis_y - grid.horizontal_lines()[0])
        / grid.horizontal.step
        * 20,
    ]
    root = ET.fromstring(svg)
    label = next(n for n in root.iter() if n.text == "y = f(x)")
    width, height = map(float, (root.get("width"), root.get("height")))
    mapped = np.column_stack(
        [
            origin[0] + (smooth[:, 0] - grid.vertical_axis_x) / grid.vertical.step * 20,
            origin[1]
            + (smooth[:, 1] - grid.horizontal_axis_y) / grid.horizontal.step * 20,
        ]
    )
    candidates = [(float(label.get("x")), float(label.get("y")))]
    candidates += [
        (x, y)
        for y in np.arange(16, height - 5, 20)
        for x in np.arange(5, width - 58, 20)
    ]

    def collisions(p):
        x, y = p
        inside = lambda points: (
            (points[:, 0] >= x - 3)
            & (points[:, 0] <= x + 58)
            & (points[:, 1] >= y - 16)
            & (points[:, 1] <= y + 3)
        ).sum()
        tx = np.linspace(x - 3, x + 58, 60)
        ty = (
            origin[1]
            - (
                tangent.logical_slope * (tx - origin[0]) / 20
                + tangent.logical_intercept
            )
            * 20
        )
        score = int(inside(mapped)) + int(inside(np.column_stack([tx, ty])))
        score += 100 * int(x - 3 <= origin[0] <= x + 58)
        score += 100 * int(y - 16 <= origin[1] <= y + 3)
        return score

    x, y = min(candidates, key=collisions)
    label.set("x", str(x))
    label.set("y", str(y))
    svg = ET.tostring(root, encoding="unicode")
    return svg, grid, tangent, markers, origin
