"""Render a recovered primitive graph with its original SVG presentation."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np

from .primitive_metadata import META, NS


def _grid(root, point, bounds, size):
    xmin, xmax, ymin, ymax = bounds
    width, height = size
    for x in range(xmin, xmax + 1):
        px = point(x, 0)[0]
        ET.SubElement(
            root,
            "line",
            {
                "x1": str(px),
                "x2": str(px),
                "y1": "0",
                "y2": str(height),
                "stroke": "#ADAAAA",
                "stroke-width": ".75",
            },
        )
    for y in range(ymin, ymax + 1):
        py = point(0, y)[1]
        ET.SubElement(
            root,
            "line",
            {
                "x1": "0",
                "x2": str(width),
                "y1": str(py),
                "y2": str(py),
                "stroke": "#ADAAAA",
                "stroke-width": ".75",
            },
        )


def _curve_path(model, knots, slopes, point, origin, cell):
    ox, oy = origin
    if "bezier_segments" in model:
        segments = np.asarray(model["bezier_segments"])
        coords = segments * np.array([cell, -cell]) + np.array([ox, oy])
        fmt = lambda p: f"{p[0]:.9f},{p[1]:.9f}"
        path = (
            "M"
            + fmt(coords[0, 0])
            + "".join("C" + " ".join(fmt(p) for p in segment[1:]) for segment in coords)
        )
    else:
        path = ""
        for i in range(len(knots) - 1):
            x0, y0 = point(*knots[i])
            x3, y3 = point(*knots[i + 1])
            dx = knots[i + 1, 0] - knots[i, 0]
            if i == 0:
                path = f"M{x0:.6f},{y0:.6f}"
            path += f"C{x0 + dx * cell / 3:.6f},{y0 - slopes[i] * dx * cell / 3:.6f} {x3 - dx * cell / 3:.6f},{y3 + slopes[i + 1] * dx * cell / 3:.6f} {x3:.6f},{y3:.6f}"
    return path


def _labels(root, point, domain, origin, width, *, show_domain=True):
    lo, hi = domain
    ox, oy = origin
    labels = ET.SubElement(
        root,
        "g",
        {
            "font-family": "Times New Roman, Times, serif",
            "font-size": "15",
            "fill": "#000000",
        },
    )

    def label(x, y, value, anchor="middle"):
        text = str(value).replace("-", "−")
        w = max(9, len(text) * 8)
        rx = x - w / 2 if anchor == "middle" else x - w if anchor == "end" else x
        ET.SubElement(
            labels,
            "rect",
            {
                "x": str(rx - 1),
                "y": str(y - 13),
                "width": str(w + 2),
                "height": "16",
                "fill": "white",
            },
        )
        ET.SubElement(
            labels, "text", {"x": str(x), "y": str(y), "text-anchor": anchor}
        ).text = text

    if show_domain:
        label(point(lo, 0)[0] - 2, oy + 14, f"{lo:g}", "end")
        label(point(hi, 0)[0] + 2, oy + 14, f"{hi:g}", "start")
    if 1.0 not in (lo, hi):
        label(point(1, 0)[0], oy + 14, "1")
    label(ox + 5, point(0, 1)[1] + 5, "1", "start")
    ET.SubElement(
        labels,
        "text",
        {"x": str(width - 10), "y": "16", "text-anchor": "end", "font-style": "italic"},
    ).text = "y = F(x)"


def _selection(root, model, selected_points, point, height):
    if selected_points is not None:
        group = ET.SubElement(root, "g", {"data-runner-diagram": "stationary_points"})
        for x, direction in (
            (float(model["span"][0]), 1),
            (float(model["span"][1]), -1),
        ):
            px = point(x, 0)[0]
            arm = direction * 9.7
            ET.SubElement(
                group,
                "polyline",
                {
                    "points": f"{px + arm},20 {px},20 {px},{height - 20} {px + arm},{height - 20}",
                    "fill": "none",
                    "stroke": "#143B8F",
                    "stroke-width": "1.25",
                    "stroke-linejoin": "round",
                    "stroke-linecap": "round",
                },
            )
        for p in selected_points:
            x, y = point(*p["svg"])
            ET.SubElement(
                group,
                "circle",
                {
                    "cx": str(x),
                    "cy": str(y),
                    "r": "2.3",
                    "fill": "#007EA5",
                    "stroke": "#007EA5",
                    "stroke-width": ".75",
                },
            )


def _load_template():
    template = ET.parse(
        Path(__file__).with_name("assets") / "primitive-extrema-template.svg"
    ).getroot()
    for element in template.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
        href = element.attrib.pop("{http://www.w3.org/1999/xlink}href", None)
        if href is not None:
            element.set("xlink:href", href)
    return template


def _add_axes(root, template, origin, size):
    ox, oy = origin
    width, height = size
    horizontal, vertical = template[24], template[25]
    horizontal.set("y1", str(oy))
    horizontal.set("y2", str(oy))
    horizontal.set("x2", str(width - 7.5))
    vertical.set("x1", str(ox))
    vertical.set("x2", str(ox))
    vertical.set("y1", str(height))
    root.extend((horizontal, vertical))


def render(model, *, selected_points=None):
    """Keep the parent SVG's style; highlight the same curve only in solutions."""
    import math

    knots = np.asarray(model["knots"])
    slopes = np.asarray(model["slopes"])
    lo, hi = map(float, model["domain"])
    cell = 20.0
    xmin = math.floor(min(lo - 1, -2))
    xmax = math.ceil(max(hi + 3, 5 if model.get("continuous_plot") else 2))
    ymin = math.floor(min(knots[:, 1].min() - 1, -2))
    ymax = math.ceil(max(knots[:, 1].max() + 1, 2))
    width = (xmax - xmin) * cell
    height = (ymax - ymin) * cell
    ox = -xmin * cell
    oy = ymax * cell
    point = lambda x, y: (ox + x * cell, oy - y * cell)
    template = _load_template()
    root = ET.Element(
        "svg",
        {
            "xmlns": NS[1:-1],
            "xmlns:xlink": "http://www.w3.org/1999/xlink",
            "width": str(width),
            "height": str(height),
            "viewBox": f"0 0 {width} {height}",
        },
    )
    ET.SubElement(root, "rect", {"width": "100%", "height": "100%", "fill": "white"})
    ET.SubElement(root, "metadata", {"id": META}).text = json.dumps(
        {"model": model, "highlighted": selected_points is not None}, sort_keys=True
    )
    _grid(root, point, (xmin, xmax, ymin, ymax), (width, height))
    _add_axes(root, template, (ox, oy), (width, height))
    path = _curve_path(model, knots, slopes, point, (ox, oy), cell)
    curve = template[28]
    curve.set("d", path)
    color = "#143B8F" if selected_points is None else "#000000"
    curve.set("stroke", color)
    curve.set("data-primitive-curve", "true")
    root.append(curve)
    endpoint_markers = []
    for xy in () if model.get("continuous_plot") else (knots[0], knots[-1]):
        x, y = point(*xy)
        endpoint_markers.append(
            ET.SubElement(
                root,
                "circle",
                {
                    "cx": str(x),
                    "cy": str(y),
                    "r": "2.2",
                    "fill": "white",
                    "stroke": color,
                    "stroke-width": ".75",
                },
            )
        )
    for index, dx, dy in (
        (38, ox - 80.582, oy - 121.3061),
        (36, ox - 80.582, 0),
        (37, width - 239.9657, oy - 121.198),
        (29, ox - 80.582, -0.4805),
        (30, width - 239.9657, oy - 121.198),
    ):
        node = template[index]
        node.set("transform", f"translate({dx} {dy})")
        root.append(node)
    _labels(
        root,
        point,
        (lo, hi),
        (ox, oy),
        width,
        show_domain=not model.get("continuous_plot"),
    )
    # Axis-label masks may erase grid lines, but must never cut the curve.
    root.remove(curve)
    root.append(curve)
    for marker in endpoint_markers:
        root.remove(marker)
        root.append(marker)
    _selection(root, model, selected_points, point, height)
    return ET.tostring(root, encoding="unicode")
