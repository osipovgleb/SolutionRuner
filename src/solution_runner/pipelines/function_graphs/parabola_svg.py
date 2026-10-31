"""Cubic source paths and inspected lattice points, without rebuilding the plot."""

import re
from xml.etree import ElementTree as ET

import numpy as np

from ..calculus.curve_levels import at_abscissa
from ..core.errors import ContentPlanError
from .linear_svg import NS, frame, snap

COLORS = ("#143B8F", "#007EA5")
_TOKEN = r"[A-Za-z]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?"


def segments(raw):
    if re.sub(_TOKEN, "", raw).strip(" ,\t\n\r"):
        raise ContentPlanError("unsupported source curve path syntax")
    tokens = re.findall(_TOKEN, raw)
    current, result, index, command = (0.0, 0.0), [], 0, None
    control = None
    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        size = {"M": 2, "m": 2, "C": 6, "c": 6, "S": 4, "s": 4}.get(command)
        if size is None or index + size > len(tokens):
            raise ContentPlanError(
                "only inspected M/C/c/S/s source curve commands are supported"
            )
        try:
            values = list(map(float, tokens[index : index + size]))
        except ValueError as exc:
            raise ContentPlanError("source curve coordinates are incomplete") from exc
        points = list(zip(values[::2], values[1::2], strict=True))
        if command.islower():
            points = [(x + current[0], y + current[1]) for x, y in points]
        if size == 4:
            reflected = tuple(
                2 * x - y for x, y in zip(current, control or current, strict=True)
            )
            points.insert(0, reflected)
        if size in (4, 6):
            control = points[-2]
            result.append([list(current)] + [list(p) for p in points])
        current = points[-1]
        index += size
        if size == 2:
            command = None
            control = None
    return result


def curves(root):
    result = {}
    for color in COLORS:
        data = [
            segment
            for n in root.iter(NS + "path")
            if n.get("stroke", "").upper() == color
            for segment in segments(n.get("d", ""))
        ]
        if data:
            result[color] = data
    if not result:
        raise ContentPlanError("inspected colored parabola paths are required")
    return result


def pixel(value, mapping):
    points = sorted((coordinate, position) for position, coordinate in mapping)
    return float(
        np.interp(float(value), [p[0] for p in points], [p[1] for p in points])
    )


def point_distance(point, curve, axes):
    xmap, ymap, _, sy = axes
    x, y = point
    samples = at_abscissa({"curve_segments": curve}, pixel(x, xmap))
    if not samples:
        raise ContentPlanError("an inspected lattice point is outside its curve path")
    return min(abs(py - pixel(y, ymap)) / sy for py, _ in samples)


def read(data, entry):
    root = ET.fromstring(data)
    axes = frame(root)
    actual = curves(root)
    if set(actual) != {c["color"] for c in entry["curves"]}:
        raise ContentPlanError("the source parabola colors disagree with inspection")
    xmap, ymap, sx, sy = axes
    markers = {
        (snap(float(n.get("cx")), xmap, sx), snap(float(n.get("cy")), ymap, sy))
        for n in root.iter(NS + "circle")
    }
    for curve in entry["curves"]:
        if any(tuple(p) not in markers for p in curve["marked_points"]):
            raise ContentPlanError(
                "the inspected marked points must exist in the source SVG"
            )
        if curve.get("vertex"):
            samples = at_abscissa(
                {"curve_segments": actual[curve["color"]]},
                pixel(curve["vertex"][0], xmap),
            )
            if (
                any(abs(slope) > 0.2 for y, slope in samples)
                or point_distance(curve["vertex"], actual[curve["color"]], axes) > 0.2
            ):
                raise ContentPlanError(
                    "the inspected vertex must coincide with the source curve extremum"
                )
        if any(
            point_distance(p, actual[curve["color"]], axes) > 0.2
            for p in curve["points"]
        ):
            raise ContentPlanError(
                "an inspected lattice point disagrees with the SVG curve"
            )
    return root, axes
