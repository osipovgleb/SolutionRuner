"""Render derivative-level diagrams and explanations."""

from html import escape
from xml.etree import ElementTree as ET

import numpy as np

from ..probability.common import UnsupportedCondition
from . import graph_derivative_levels, raster_primitive


def _render(model):
    return raster_primitive.render(model).replace("y = F(x)", "y = f′(x)")


def _solution_svg(data, q, entry, points, model):
    source = _render(model) if model is not None else data.decode()
    root = ET.fromstring(source)
    for node in root.iter():
        style = node.attrib.pop("style", None)
        if style:
            for declaration in style.split(";"):
                if not declaration.strip():
                    continue
                name, value = declaration.split(":", 1)
                if name.strip() not in {"stop-color", "stop-opacity"}:
                    raise UnsupportedCondition(
                        "unsupported style in the native solution SVG"
                    )
                node.set(name.strip(), value.strip())
    # Reuse the family drawing routine in the native SVG coordinate frame.
    if model is not None:
        knots = np.asarray(model["knots"])
        import math

        ox = -math.floor(min(float(model["domain"][0]) - 1, -2)) * 20
        oy = math.ceil(max(knots[:, 1].max() + 1, 2)) * 20
        entry = {**entry, "svg_origin": [ox, oy], "svg_unit": 20}
        points = [(ox + x, oy + y) for x, y in points]
    entry = {**entry, "svg_level_layer": 1, "diagram_style": "green_level"}
    return graph_derivative_levels.render_svg(
        entry, ET.tostring(root, encoding="unicode"), q, points
    )


def proof(q, result):
    def inline(x):
        return '<span data-inline-latex="' + escape(x, quote=True) + '"></span>'

    from .common import answer

    k = answer(q.slope).replace(",", "{,}")
    return (
        "<p>Угловой коэффициент данной прямой равен "
        + inline(k)
        + ", поэтому ищем точки, в которых "
        + inline("f'(x)=" + k)
        + ".</p>"
        + "<p>Проведём горизонтальную прямую "
        + inline("y=" + k)
        + ". Посчитаем общие точки этой прямой и графика производной на заданном интервале. Их количество — "
        + result
        + ".</p>"
    )
