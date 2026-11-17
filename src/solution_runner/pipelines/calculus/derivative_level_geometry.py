"""Recover derivative curve geometry and intersect it with a level."""

from itertools import pairwise
from xml.etree import ElementTree as ET

import numpy as np

from ..probability.common import UnsupportedCondition
from . import curve_levels, primitive_svg
from .primitive_metadata import NS


def _native_entry(data, question):
    frame, extrema = primitive_svg.read(data, question)
    root = ET.fromstring(data)
    axes = []
    for n in root.iter(NS + "line"):
        if n.get("stroke", "").lower() not in ("black", "#000000", "#000"):
            continue
        x1, y1, x2, y2 = (float(n.get(k, "0")) for k in ("x1", "y1", "x2", "y2"))
        if abs(y2 - y1) < 0.001 and abs(x2 - x1) > frame["svg_unit"] * 3:
            axes.append((abs(x2 - x1), y1))
    if not axes:
        raise UnsupportedCondition(
            "the native derivative graph needs a horizontal coordinate axis"
        )
    oy = max(axes)[1]
    segments = []
    for n in root.iter(NS + "path"):
        if n.get("stroke", "").lower() == "#143b8f":
            segments.extend(primitive_svg._segments(n.get("d", "")))
    segments = [
        s if s[-1, 0] > s[0, 0] else s[::-1]
        for s in segments
        if abs(s[-1, 0] - s[0, 0]) > 1e-6
    ]
    segments.sort(key=lambda s: s[0, 0])
    unit = frame["svg_unit"]
    for before, after in pairwise(segments):
        p = before[-1]
        incoming = p[1] - before[-2, 1]
        outgoing = after[1, 1] - after[0, 1]
        if incoming * outgoing < 0 and not any(
            abs(v["svg"][0] - p[0]) < unit * 0.05 for v in extrema
        ):
            extrema.append({"svg": p.tolist()})
    extrema.sort(key=lambda v: v["svg"][0])
    nodes = []
    for p, endpoint in [
        (segments[0][0], True),
        *[(n["svg"], False) for n in extrema],
        (segments[-1][-1], True),
    ]:
        y = (oy - float(p[1])) / unit
        node = {"svg": list(p), "endpoint": endpoint}
        if abs(y - round(y)) < 0.035:
            node["y"] = str(round(y))
        else:
            node["y_bounds"] = [str(y - 0.02), str(y + 0.02)]
        nodes.append(node)
    return {
        "svg_origin": [frame["svg_origin"][0], oy],
        "svg_unit": unit,
        "curve_segments": [s.tolist() for s in segments],
        "curve_nodes": nodes,
    }


def _model_entry(model):
    segments = np.asarray(model["bezier_segments"])
    nodes = []
    anchors = [
        (segments[0, 0], True),
        *[((p["x"], p["y"]), False) for p in model["extrema"]],
        (segments[-1, -1], True),
    ]
    for p, endpoint in anchors:
        y = float(p[1])
        node = {"svg": [float(p[0]) * 20, -y * 20], "endpoint": endpoint}
        if abs(y - round(y)) < 0.06:
            node["y"] = str(round(y))
        else:
            node["y_bounds"] = [str(y - 0.06), str(y + 0.06)]
        nodes.append(node)
    transformed = segments.copy() * 20
    transformed[:, :, 1] *= -1
    return {
        "svg_origin": [0, 0],
        "svg_unit": 20,
        "curve_segments": transformed.tolist(),
        "curve_nodes": nodes,
    }


def _intersections(entry, level):
    points = curve_levels.svg_intersections(entry, level)
    nodes = entry["curve_nodes"]
    for i, node in enumerate(nodes):
        if curve_levels.ordinate_sign(node, level) != 0:
            continue
        left = nodes[max(0, i - 1)]["svg"][0]
        right = nodes[min(len(nodes) - 1, i + 1)]["svg"][0]
        points = [p for p in points if not left - 1e-6 <= p[0] <= right + 1e-6]
        if not node.get("endpoint", False):
            points.append(
                (
                    node["svg"][0],
                    entry["svg_origin"][1] - float(level) * entry["svg_unit"],
                )
            )
    unique = curve_levels.distinct_points(
        points, nodes[0]["svg"][0], nodes[-1]["svg"][0]
    )
    if len(unique) != curve_levels.count(nodes, level):
        raise UnsupportedCondition(
            "the SVG intersections and monotone-arc count disagree"
        )
    return unique
