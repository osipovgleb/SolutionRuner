"""Match circular endpoint markers at multiple scales."""

import cv2
import numpy as np


def ring_responses(marker_dark, step, maximum_radius, radius_count):
    response = np.full(marker_dark.shape, -1.0, dtype=np.float32)
    radius_map = np.zeros(marker_dark.shape, dtype=np.float32)
    for radius in np.linspace(step * 0.035, step * maximum_radius, radius_count):
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
    return response, radius_map
