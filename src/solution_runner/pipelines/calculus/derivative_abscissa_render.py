"""Horizontal derivative levels and a grid projection for the requested abscissa."""

from html import escape
from xml.etree import ElementTree as ET

from . import derivative_level_render, tangent_native
from .common import answer


def inline(x):
    return '<span data-inline-latex="' + escape(x, quote=True) + '"></span>'


def solution_svg(data, q, entry, points, model):
    source = tangent_native.presentation(data).encode() if model is None else data
    svg = derivative_level_render._solution_svg(source, q, entry, points, model)
    if q.count:
        return svg
    root = ET.fromstring(svg)
    ox, oy = entry["svg_origin"]
    if model is not None:
        # The rendered raster SVG uses a translated 20 px coordinate frame.
        import math

        import numpy as np

        ox = -math.floor(min(float(model["domain"][0]) - 1, -2)) * 20
        oy = math.ceil(max(np.asarray(model["knots"])[:, 1].max() + 1, 2)) * 20
        point = min(points)
        x, y = ox + point[0], oy + point[1]
        raw = point[0] / 20
    else:
        x, y = min(points)
        raw = (x - ox) / entry.get("x_unit", entry["svg_unit"])
    g = ET.SubElement(root, tangent_native.NS + "g", {"data-runner-layer": "abscissa"})
    ET.SubElement(
        g,
        tangent_native.NS + "line",
        {
            "x1": str(x),
            "y1": str(y),
            "x2": str(x),
            "y2": str(oy),
            "stroke": "#143B8F",
            "stroke-width": "0.75",
            "stroke-dasharray": "3,2",
        },
    )
    # Keep a separate numeric coordinate legible over old export glyphs.
    ET.SubElement(
        g,
        tangent_native.NS + "rect",
        {
            "x": str(x - 9),
            "y": str(oy + 2),
            "width": "18",
            "height": "16",
            "fill": "white",
        },
    )
    t = ET.SubElement(
        g,
        tangent_native.NS + "text",
        {
            "x": str(x),
            "y": str(oy + 15),
            "text-anchor": "middle",
            "font-family": "Times New Roman, serif",
            "font-size": "12",
            "fill": "#143B8F",
        },
    )
    t.text = str(round(raw))
    return ET.tostring(root, encoding="unicode")


def proof(q, result):
    if q.count:
        return derivative_level_render.proof(q, result)
    k = answer(q.slope).replace(",", "{,}")
    opening = (
        "Данная прямая параллельна оси абсцисс, поэтому её угловой коэффициент равен "
        if q.comparison is None
        else "Угловой коэффициент данной прямой равен "
    )
    ending = (
        "Наименьшая абсцисса точки пересечения — "
        if q.smallest
        else "Абсцисса точки пересечения — "
    )
    return (
        "<p>"
        + opening
        + inline(k)
        + ", поэтому ищем точки, в которых "
        + inline("f'(x)=" + k)
        + ".</p>"
        + "<p>Проведём горизонтальную прямую "
        + inline("y=" + k)
        + ". "
        + ending
        + inline("x=" + result)
        + ".</p>"
    )
