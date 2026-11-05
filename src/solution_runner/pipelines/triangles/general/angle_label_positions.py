"""Place outlined triangle labels without crossing strokes or other labels."""

import itertools
import math

from ...core.errors import ContentPlanError
from ..right.construction_svg import _tag


def _intersects(p, q, box):
    x, y, w, h = box
    low, high = 0.0, 1.0
    for axis, start, end in [(0, x - 1, x + w + 1), (1, y - 1, y + h + 1)]:
        delta = q[axis] - p[axis]
        if abs(delta) < 1e-10:
            if not start <= p[axis] <= end:
                return False
        else:
            first, last = sorted(((start - p[axis]) / delta, (end - p[axis]) / delta))
            low, high = max(low, first), min(high, last)
            if low > high:
                return False
    return True


def _position(root, point, w, h, boxes, preferred, *, max_distance=None):
    segments = []
    for line in root.findall(_tag("line")):
        segments.append(
            tuple(
                tuple(float(line.get(axis + str(i))) for axis in ["x", "y"])
                for i in [1, 2]
            )
        )
    for polyline in root.findall(_tag("polyline")):
        points = [
            tuple(map(float, p.split(","))) for p in polyline.get("points").split()
        ]
        segments.extend(itertools.pairwise(points))
    x, y = point
    candidates = [preferred]
    for gap in [4, 8, 12, 20, 30, 40]:
        candidates.extend(
            [
                (x - w - gap, y - h - gap),
                (x + gap, y - h - gap),
                (x - w - gap, y + gap),
                (x + gap, y + gap),
                (x - w / 2, y - h - gap),
                (x - w / 2, y + gap),
                (x - w - gap, y - h / 2),
                (x + gap, y - h / 2),
            ]
        )
    for x, y in candidates:
        if (
            max_distance is not None
            and math.dist(point, (x + w / 2, y + h / 2)) > max_distance
        ):
            continue
        if any(
            x < bx + bw + 2 and x + w + 2 > bx and y < by + bh + 2 and y + h + 2 > by
            for bx, by, bw, bh in boxes
        ):
            continue
        if not any(_intersects(p, q, (x, y, w, h)) for p, q in segments):
            return x, y
    raise ContentPlanError(
        "the triangle labels cannot be placed without crossing the construction"
    )
