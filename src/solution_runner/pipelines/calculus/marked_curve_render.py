"""Colour the function curve using its reviewed monotonic intervals."""

from itertools import pairwise
from xml.etree import ElementTree as ET

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter1d

from solution_runner.converters.graph_contrast_paths import _bezier_path

from ..probability.common import UnsupportedCondition
from . import primitive_svg, tangent_native

BLUE = "#1765a8"
RED = "#b42318"
GREEN = "#15803d"
SIGN_COLORS = {-1: GREEN, 0: "#475569", 1: RED}
DISPLAY_WIDTH = 370


def display_size(root):
    _, _, width, height = map(float, root.get("viewBox").split())
    root.set("width", str(DISPLAY_WIDTH))
    root.set("height", f"{DISPLAY_WIDTH * height / width:.3f}")


def function_segments(source):
    root = ET.fromstring(tangent_native.presentation(source))
    segments = []
    for node in root.iter(tangent_native.NS + "path"):
        if node.get("stroke", "").lower() == "#143b8f":
            segments.extend(primitive_svg._segments(node.get("d", "")))
    return _left_to_right(segments)


def _left_to_right(segments):
    return sorted(
        (s if s[0, 0] < s[-1, 0] else s[::-1] for s in segments),
        key=lambda s: s[0, 0],
    )


def chart_from_turns(segments, turns):
    if not segments or not turns:
        raise UnsupportedCondition("the curve and turning points must be known")
    if any(a["kind"] == b["kind"] for a, b in pairwise(turns)):
        raise UnsupportedCondition("successive turning points must alternate")
    return {
        "left": float(segments[0][0][0]),
        "right": float(segments[-1][-1][0]),
        "initial": 1 if turns[0]["kind"] == "max" else -1,
        "turns": [p["svg"] for p in turns],
    }


def chart_from_curve(entry):
    from .monotonic_sum_input import ordinate, stationary

    segments = _left_to_right(map(np.asarray, entry["curve_segments"]))
    entry = {**entry, "curve_segments": segments, "svg_unit": entry.get("svg_unit", 20)}
    candidates = stationary(entry)
    limits = [segments[0][0], *candidates, segments[-1][-1]]
    turns = []
    for left, (x, y), right in zip(limits, limits[1:], limits[2:]):
        before = ordinate(entry, (left[0] + x) / 2)
        after = ordinate(entry, (x + right[0]) / 2)
        if (before - y) * (after - y) > 0:
            turns.append({"svg": (x, y), "kind": "max" if y < before else "min"})
    return chart_from_turns(segments, turns)


def _raster_curve(ink, ox, oy, left, right, *, reviewed=False):
    mask = ink.copy()
    width = ink.shape[1]
    radius = max(3, round(width * (0.009 if reviewed else 0.006)))
    mask[:, max(0, ox - radius) : ox + radius + 1] = False
    mask[max(0, oy - radius) :] = False
    if reviewed:
        mask[:, :left] = False
        mask[:, right + 1 :] = False
    _, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
    component_width = (
        round(width * 0.04) if reviewed else max(22, round((right - left) * 0.065))
    )
    curve = np.isin(
        labels,
        [
            i
            for i, (x, _, w, _, _) in enumerate(stats)
            if i and w >= component_width and x < right and x + w > left
        ],
    )
    first = np.argmax(curve, axis=0)
    columns = np.flatnonzero(curve.any(axis=0))
    columns = columns[(left <= columns) & (columns <= right)]
    if len(columns) < (right - left) * 0.75:
        raise UnsupportedCondition(
            "the raster curve cannot be isolated from its guides"
        )
    if reviewed:
        x = np.arange(columns[0], columns[-1] + 1)
        offset = np.minimum(4, (curve.sum(axis=0)[columns] - 1) / 2)
    else:
        x = np.arange(left, right + 1)
        offset = max(1.5, width * 0.0028)
    y = gaussian_filter1d(
        np.interp(x, columns, first[columns] + offset), 2.5 if reviewed else 2
    )
    if reviewed:
        distances = cv2.distanceTransform(
            (~ink).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        error = distances[np.rint(y).astype(int), x]
        if np.max(error) > width * 0.027 or np.mean(error > width * 0.012) > 0.015:
            raise UnsupportedCondition(
                "the fitted curve departs from the original drawing"
            )
    return x, y


def render(
    source,
    entry,
    points,
    selected,
    *,
    raster_gray=None,
    outline=None,
    catalog_style=False,
    signed=False,
    project_marks=False,
):
    chart = entry["function_sign_chart"]
    limits = [chart["left"], *(x for x, _ in chart["turns"]), chart["right"]]
    if any(a >= b for a, b in pairwise(limits)):
        raise UnsupportedCondition("monotonic curve intervals must be ordered")
    endpoints = []
    if entry.get("extension") == ".png":
        ink = np.asarray(raster_gray(source)) <= 150
        width = ink.shape[1]
        ox, oy = map(round, entry["svg_origin"])
        xx, yy = _raster_curve(ink, ox, oy, round(limits[0]), round(limits[-1]))
        cleaned = ink.copy()
        for point in points:
            x, y = map(round, point["svg"])
            half = max(2, round(width * 0.005))
            lower, upper = sorted((y, oy))
            cleaned[lower + 1 : upper, max(0, x - half) : x + half + 1] = False
        # Remove the black raster curve around the recovered centreline.
        eraser = np.zeros_like(cleaned, dtype=np.uint8)
        cv2.polylines(
            eraser,
            [np.rint(np.column_stack((xx, yy))).astype(np.int32)],
            False,
            1,
            thickness=max(10, round(width * 0.019)),
        )
        cleaned[eraser.astype(bool)] = False
        # Preserve the ordinate axis where the curve crosses it.
        axis_half = max(1, round(width * 0.0025))
        cleaned[:, ox - axis_half : ox + axis_half + 1] = ink[
            :, ox - axis_half : ox + axis_half + 1
        ]
        root = outline(cleaned)
    else:
        root = ET.fromstring(tangent_native.presentation(source))
        width = float(root.get("viewBox").split()[2])
        parents = {child: parent for parent in root.iter() for child in parent}
        if selected is None:
            for node in root.iter():
                if node.get("stroke", "").lower() == "#143b8f":
                    node.set("stroke-width", f"{width * 0.0035:.3f}")
            return ET.tostring(root, encoding="unicode")
        for node in list(root.iter()):
            if not signed and node.get("stroke-dasharray") and node in parents:
                parent = parents.pop(node)
                parent.remove(node)
        for node in list(root.iter()):
            blue_stroke = node.get("stroke", "").lower() == "#143b8f"
            blue_fill = node.get("fill", "").lower() == "#143b8f"
            if (
                (
                    node.tag in (tangent_native.NS + "path", tangent_native.NS + "line")
                    and blue_stroke
                    and node.get("fill") in (None, "none")
                )
                or (
                    node.tag == tangent_native.NS + "circle"
                    and (blue_stroke or blue_fill)
                )
            ) and node in parents:
                if (
                    signed
                    and node.tag == tangent_native.NS + "circle"
                    and node.get("fill", "").lower() in {"white", "#fff", "#ffffff"}
                ):
                    endpoints.append(node)
                parents[node].remove(node)
        samples = np.concatenate(
            [
                np.asarray(
                    [
                        primitive_svg._at(np.asarray(segment), t)
                        for t in np.linspace(0, 1, 100)
                    ]
                )
                for segment in entry["curve_segments"]
            ]
        )
        samples = samples[np.argsort(samples[:, 0], kind="stable")]
        xx, yy = samples.T

    group = ET.SubElement(
        root,
        tangent_native.NS + "g",
        {"data-runner-diagram": "monotonic_function_curve"},
    )
    for i, (a, b) in enumerate(pairwise(limits)):
        middle = xx[(a < xx) & (xx < b)]
        xs = np.r_[a, middle, b]
        ys = np.interp(xs, xx, yy)
        if entry.get("extension") == ".png":
            coords = cv2.approxPolyDP(
                np.column_stack((xs, ys)).astype(np.float32), 0.6, False
            ).reshape(-1, 2)
        else:
            coords = np.column_stack((xs, ys))
        d = (
            _bezier_path(coords, 0.22)[0]
            if catalog_style
            else "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in coords)
        )
        ET.SubElement(
            group,
            tangent_native.NS + "path",
            {
                "d": d,
                "stroke": RED
                if chart["initial"] * (-1) ** i > 0
                else GREEN
                if signed
                else BLUE,
                "stroke-width": f"{width * (0.0035 if catalog_style else 0.0045):.3f}",
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
                "fill": "none",
            },
        )
    marks = ET.SubElement(
        root, tangent_native.NS + "g", {"data-runner-diagram": "selected_markers"}
    )
    marks.extend(endpoints)
    for point in points:
        x, y = point["svg"]
        new_y = float(np.interp(x, xx, yy))
        if abs(y - new_y) > width * 0.035:
            raise UnsupportedCondition("the coloured curve misses a labelled point")
        if project_marks or signed and entry.get("extension") == ".png":
            axis = entry["svg_origin"][1]
            ET.SubElement(
                marks,
                tangent_native.NS + "line",
                x1=str(x),
                x2=str(x),
                y1=str(axis),
                y2=str(new_y),
                stroke="#444",
                attrib={
                    "stroke-width": f"{width * 0.002:.3f}",
                    "stroke-dasharray": f"{width * 0.010:.2f} {width * 0.006:.2f}",
                },
            )
        ET.SubElement(
            marks,
            tangent_native.NS + "circle",
            {
                "cx": f"{x:.3f}",
                "cy": f"{new_y:.3f}",
                "r": f"{width * 0.010:.3f}",
                "fill": SIGN_COLORS[point["sign"]]
                if signed
                else GREEN
                if point in selected
                else RED,
                "stroke": "white",
                "stroke-width": f"{width * 0.002:.3f}",
            },
        )
    if signed:
        display_size(root)
    return ET.tostring(root, encoding="unicode")


def tangent_raster(
    ink,
    origin,
    points,
    *,
    course_style=False,
    indexed=False,
    derivative=False,
    function_chart=None,
    selected=None,
    signed=False,
):
    """Recover the curve centreline separately from axes, guides and labels."""
    height, width = ink.shape
    ox, oy = map(round, origin)
    if function_chart:
        xs, ys = _raster_curve(
            ink,
            ox,
            oy,
            round(function_chart["left"]),
            round(function_chart["right"]),
            reviewed=True,
        )
        reviewed = []
        for point in points:
            x, old_y = point["svg"]
            y = float(np.interp(x, xs, ys))
            if not xs[0] <= x <= xs[-1] or abs(old_y - y) > width * 0.032:
                raise UnsupportedCondition("the recovered curve misses a marked point")
            reviewed.append({**point, "svg": [x, y]})
        selected_labels = {p["label"] for p in selected or ()}
        points = reviewed
    else:
        band = max(4, round(width * 0.005))
        mask = ink.copy()
        for x, _ in [origin, *(p["svg"] for p in points)]:
            x = round(x)
            mask[:, max(0, x - band) : x + band + 1] = False
        mask[max(0, oy - band) : oy + band + 1] = False
        mask[:band, :] = False
        mask[:, -band:] = False
        _, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8))
        long = [
            i
            for i, (_, _, w, h, n) in enumerate(stats)
            if i and w >= width * 0.025 and h >= width * 0.007 and n >= width * 0.09
        ]
        curve = np.isin(labels, long)
        columns = np.flatnonzero(curve.any(axis=0))
        if not len(columns) or len(columns) < width * 0.64:
            raise UnsupportedCondition(
                "the comparison curve is incomplete after removing guides"
            )
        rows = np.asarray([np.median(np.flatnonzero(curve[:, x])) for x in columns])
        marker_x, marker_y = np.asarray([p["svg"] for p in points]).T
        check = np.interp(marker_x, columns, rows)
        if np.any(abs(check - marker_y) > width * 0.026):
            raise UnsupportedCondition(
                "the clean comparison curve misses a marked contact"
            )
        xs = np.arange(columns[0], columns[-1] + 1)
        ys = gaussian_filter1d(np.interp(xs, columns, rows), 2.4)
        # The tangent segment meets the actual recovered contact, including gaps from guide removal.
        for x, y in zip(marker_x, marker_y, strict=True):
            index = round(x) - xs[0]
            if not 0 <= index < len(xs):
                continue
            radius = width * 0.010
            weight = np.maximum(0, 1 - abs(xs - x) / radius)
            ys += weight**2 * (y - ys[index])
    left = xs[0] - width * 0.022 if function_chart else 0
    right = xs[-1] + width * 0.048 if function_chart else width
    top = min(ys) - width * 0.053 if function_chart else 0
    bottom = oy + width * 0.050 if function_chart else height
    root = ET.Element(
        tangent_native.NS + "svg",
        viewBox=f"{left} {top} {right - left} {bottom - top}"
        if function_chart
        else f"0 0 {width} {height}",
        width=str(width),
        height=str(height),
    )
    if signed:
        display_size(root)
    plot = ET.SubElement(
        root,
        tangent_native.NS + "g",
        {
            "font-family": "Times New Roman,serif",
            "font-size": str(width * 0.033),
        },
    )
    axis_width = width * 0.0023
    pad = 0.019 * width
    tip = 0.021 * width
    right -= pad
    pad_top = top + pad
    for x1, y1, x2, y2 in [
        (left + pad, oy, right, oy),
        (ox, bottom - pad, ox, pad_top),
    ]:
        ET.SubElement(
            plot,
            tangent_native.NS + "line",
            {
                "x1": str(x1),
                "x2": str(x2),
                "y1": str(y1),
                "y2": str(y2),
                "stroke": "#161616",
                "stroke-width": str(axis_width),
            },
        )
    for vertices in [
        ((right, oy), (right - tip, oy - tip * 0.27), (right - tip, oy + tip * 0.27)),
        (
            (ox, pad_top),
            (ox - tip * 0.27, pad_top + tip),
            (ox + tip * 0.27, pad_top + tip),
        ),
    ]:
        ET.SubElement(
            plot,
            tangent_native.NS + "polygon",
            {
                "points": " ".join(f"{x:.2f},{y:.2f}" for x, y in vertices),
                "fill": "#161616",
            },
        )
    origin_x = ox - width * 0.034
    origin_y = oy + width * 0.034
    if function_chart and any(
        abs(p["svg"][0] - origin_x) < width * 0.028 for p in points
    ):
        origin_y = oy - width * 0.012
    for text, x, y in [
        ("x", right - tip, oy + width * 0.032),
        ("y", ox - width * 0.023, pad_top + width * 0.024),
        *([("O", origin_x, origin_y)] if function_chart else []),
    ]:
        ET.SubElement(
            plot,
            tangent_native.NS + "text",
            {
                "x": str(x),
                "y": str(y),
                "font-style": "italic",
            },
        ).text = text
    for point in points:
        x, y = point["svg"]
        if selected is None or signed:
            ET.SubElement(
                plot,
                tangent_native.NS + "line",
                {
                    "x1": str(x),
                    "x2": str(x),
                    "y1": str(oy),
                    "y2": str(y),
                    "stroke": "#222222" if function_chart else "#70757f",
                    "stroke-width": str(axis_width * 0.8),
                    "stroke-dasharray": f"{width * 0.010:.2f} {width * 0.006:.2f}",
                },
            )
        label = ET.SubElement(
            plot,
            tangent_native.NS + "text",
            {
                "x": str(x),
                "y": str(oy + width * (0.034 if y < oy else -0.012)),
                "text-anchor": "middle",
            },
        )
        if indexed:
            label.text = "x"
            label.set("font-style", "italic")
            ET.SubElement(
                label,
                tangent_native.NS + "tspan",
                {
                    "baseline-shift": "sub",
                    "font-size": "70%",
                },
            ).text = str(point["label"])
        else:
            label.text = str(point["label"]).replace("-", "−")
    if function_chart:
        cuts = [xs[0], xs[-1]]
        if selected is not None:
            cuts[1:1] = [x for x, _ in function_chart["turns"] if xs[0] < x < xs[-1]]
        for index, (a, b) in enumerate(pairwise(cuts)):
            x = np.r_[a, xs[(a < xs) & (xs < b)][::3], b]
            d, _ = _bezier_path(np.column_stack((x, np.interp(x, xs, ys))), 1.5)
            color = (
                "#143B8F"
                if selected is None
                else RED
                if function_chart["initial"] * (-1) ** index > 0
                else GREEN
                if signed
                else BLUE
            )
            ET.SubElement(
                plot,
                tangent_native.NS + "path",
                {
                    "d": d,
                    "fill": "none",
                    "stroke": color,
                    "stroke-width": str(width * 0.0035),
                    "stroke-linecap": "round",
                },
            )
        ET.SubElement(
            plot,
            tangent_native.NS + "text",
            {
                "x": str(left + width * 0.04),
                "y": str(top + width * 0.038),
                "font-style": "italic",
                "fill": "#000000",
            },
        ).text = "y = f(x)"
    else:
        coords = cv2.approxPolyDP(
            np.column_stack((xs, ys)).astype(np.float32), 0.7, False
        ).reshape(-1, 2)
        ET.SubElement(
            plot,
            tangent_native.NS + "path",
            {
                "d": "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in coords),
                "fill": "none",
                "stroke": "#143B8F" if course_style else "#20242e",
                "stroke-width": str(width * (0.0035 if course_style else 0.0042)),
                "stroke-linecap": "round",
                "stroke-linejoin": "round",
            },
        )
    if course_style:
        for point in points:
            x, y = point["svg"]
            ET.SubElement(
                plot,
                tangent_native.NS + "circle",
                {
                    "cx": str(x),
                    "cy": str(y),
                    "r": str(width * (0.009 if selected is not None else 0.0055)),
                    "fill": SIGN_COLORS[point["sign"]]
                    if signed
                    else "#143B8F"
                    if selected is None
                    else "#15803d"
                    if point["label"] in selected_labels
                    else RED,
                },
            )
        if not function_chart:
            label_width = round(width * 0.16)
            for x, y in (
                (round(width * 0.72), round(height * 0.14)),
                (round(width * 0.67), round(height * 0.79)),
                (round(width * 0.08), round(height * 0.15)),
            ):
                y_values = ys[(x - pad / 2 <= xs) & (xs <= x + label_width)]
                if len(y_values) and min(abs(y_values - y)) > width * 0.044:
                    ET.SubElement(
                        plot,
                        tangent_native.NS + "text",
                        {
                            "x": str(x),
                            "y": str(y),
                            "font-style": "italic",
                            "fill": "#143B8F",
                        },
                    ).text = "y = f′(x)" if derivative else "y = f(x)"
                    break
    return root
