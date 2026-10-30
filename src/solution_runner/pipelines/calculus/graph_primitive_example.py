"""A continuous primitive of a reviewed piecewise derivative, in source style."""

import math

import numpy as np

from ..probability.common import UnsupportedCondition


def render(entry):
    segments = entry["curve_segments"]
    holes = [p for p in entry["zero_points"] if not p.get("defined", True)]
    if len(holes) != 1 or len(segments) < 2:
        raise UnsupportedCondition(
            "the primitive example needs one reviewed derivative break"
        )
    lower, upper = entry["monotonic_domain"]
    hole = holes[0]["x"]
    origin, unit = entry["svg_origin"], entry["svg_unit"]
    branches = [[], []]
    for segment in segments:
        branches[int(segment[0][0] > origin[0] + (hole - 0.1) * unit)].append(segment)
    result = []
    offset = 0
    at_hole = None
    for branch, a, b in zip(branches, [lower, hole], [hole, upper], strict=True):
        if not branch:
            raise UnsupportedCondition("both derivative branches are required")
        start, stop = branch[0][0][0], branch[-1][-1][0]
        for segment in branch:
            p = np.asarray(segment, dtype=float)
            coefficients = [
                p[3] - 3 * p[2] + 3 * p[1] - p[0],
                3 * (p[2] - 2 * p[1] + p[0]),
                3 * (p[1] - p[0]),
                p[0],
            ]
            x = np.poly1d([v[0] for v in coefficients])
            g = np.poly1d([-v[1] / unit for v in coefficients]) + origin[1] / unit
            scaled_x = (x - start) * (b - a) / (stop - start) + a
            integral = np.polyint(g * np.polyder(scaled_x))
            initial = integral(0)
            points = [
                (float(scaled_x(t)), float(offset + integral(t) - initial))
                for t in np.linspace(0, 1, 65)
            ]
            result.extend(points)
            offset = points[-1][1]
        if at_hole is None:
            at_hole = offset
    result = [(x, y - at_hole) for x, y in result]
    ymin = math.floor(min(y for _, y in result)) - 1
    ymax = math.ceil(max(y for _, y in result)) + 1
    xmin, xmax = lower - 1, upper + 1
    scale = 22
    width, height = (xmax - xmin) * scale, (ymax - ymin) * scale

    def xy(x, y):
        return (x - xmin) * scale, (ymax - y) * scale

    def path(points):
        return " ".join(
            ("M" if i == 0 else "L") + f"{xy(x, y)[0]:.3f},{xy(x, y)[1]:.3f}"
            for i, (x, y) in enumerate(points)
        )

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    svg += '<rect width="100%" height="100%" fill="white"/><g stroke="#C0BFBF" stroke-width=".75">'
    for x in range(xmin, xmax + 1):
        px, _ = xy(x, 0)
        svg += f'<path d="M{px},0V{height}"/>'
    for y in range(ymin, ymax + 1):
        _, py = xy(0, y)
        svg += f'<path d="M0,{py}H{width}"/>'
    ox, oy = xy(0, 0)
    svg += f'</g><g stroke="black" fill="black" stroke-width="1"><path d="M0,{oy}H{width - 5} M{ox},{height}V5"/><path d="M{width - 2},{oy}l-10,-4 3,4 -3,4z M{ox},2l-4,10 4,-3 4,3z"/></g>'
    svg += f'<path d="{path(result)}" fill="none" stroke="#143B8F" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"/>'
    for (x, y), label, closed, abscissa in zip(
        [result[0], (hole, 0), result[-1]],
        "ABC",
        [entry["domain_closed"][0], True, entry["domain_closed"][1]],
        [lower, hole, upper],
        strict=True,
    ):
        px, py = xy(x, y)
        svg += f'<path d="M{px},{py}V{oy}" stroke="#777" stroke-width=".75" stroke-dasharray="5 3"/>'
        svg += f'<circle cx="{px}" cy="{py}" r="2.4" stroke="#143B8F" stroke-width=".8" fill="{"#143B8F" if closed else "white"}"/>'
        svg += f'<text x="{px + 5}" y="{py - 5}" font-family="Times New Roman,serif" font-style="italic" font-size="14">{label}</text>'
        svg += f'<text x="{px - 9}" y="{oy + 16}" font-family="Times New Roman,serif" font-size="13">{abscissa}</text>'
    svg += f'<g font-family="Times New Roman,serif" font-style="italic" font-size="15"><text x="{width - 12}" y="{oy + 17}">x</text><text x="{ox - 12}" y="13">y</text><text x="{ox + 5}" y="{oy + 16}">O</text></g></svg>'
    return svg
