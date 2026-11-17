"""Locate the open endpoint markers of a horizontal-tangent source graph."""

import cv2
import numpy as np

from solution_runner.converters import graph_png_to_svg_by_contrast as base


def match_markers(clean, grid, rough, bounds):
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
    markers = []
    ends = []
    for side, bound in enumerate(bounds):
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
        markers.append(
            {
                "x": x,
                "y": y,
                "radius": radius,
                "quality": quality,
                "ring_coverage": coverage,
                "forecast_y": forecast,
            }
        )
    return ends, markers
