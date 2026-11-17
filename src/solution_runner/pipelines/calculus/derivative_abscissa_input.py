"""Derivative levels with an abscissa request, measured in the source grid."""

from copy import deepcopy
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from xml.etree import ElementTree as ET

import numpy as np
from bs4 import BeautifulSoup

from ..equations.linear_system_intervals import Interval
from ..probability.common import UnsupportedCondition, normalize
from . import derivative_level_input as shared
from . import (
    graph_derivative_levels,
    graph_input,
    graph_stationary,
    primitive_svg,
    raster_primitive,
    tangent_native,
)
from .derivative_level_geometry import _intersections, _model_entry, _native_entry


@dataclass(frozen=True)
class Question(graph_derivative_levels.Question):
    smallest: bool = False


def read(context):
    clean = deepcopy(context)
    content = clean["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    keys = condition.get("asset_keys", [])
    if len(keys) != 1:
        raise UnsupportedCondition("one derivative graph is required")
    asset = next(a for a in content["assets"] if a["asset_key"] == keys[0])
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) != 1 or images[0].get("data-asset-id") != asset["asset_id"]:
        raise UnsupportedCondition("the visible derivative graph must match its asset")
    images[0].decompose()
    condition["html"], condition["asset_keys"], content["assets"] = str(soup), [], []
    text = normalize(graph_input._read_text(clean)[4])
    text = text.replace("график функции y=f'(x)—", "график y=f'(x)—")
    smallest = "Найдите наименьшую абсциссу" in text
    if not text.split(". ", 1)[-1].startswith("Найдите количество"):
        text = text.replace("к графику функции f(x)", "к графику функции y=f(x)")
    q = graph_derivative_levels.parse(
        text.replace("Найдите наименьшую абсциссу", "Найдите абсциссу")
    )
    q = Question(q.count, q.slope, q.comparison, q.domain, smallest)
    return (
        q,
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        ),
        asset,
    )


def native(data, q):
    source = tangent_native.presentation(data).encode()
    root = ET.fromstring(source)
    lines = tangent_native.straight_segments(root)
    black = [
        p
        for n, p in lines
        if n.get("stroke", "").lower() in ("black", "#000000", "#000")
    ]
    hs = [p for p in black if abs(p[3] - p[1]) < 0.3 and abs(p[2] - p[0]) > 20]
    vs = [p for p in black if abs(p[2] - p[0]) < 0.3 and abs(p[3] - p[1]) > 20]
    if not hs or not vs:
        raise UnsupportedCondition("native derivative axes are required")
    ox = max(vs, key=lambda p: abs(p[3] - p[1]))[0]
    oy = max(hs, key=lambda p: abs(p[2] - p[0]))[1]
    gray = [p for n, p in lines if n.get("stroke", "").lower() == "#adaaaa"]
    xs = sorted({p[0] for p in gray if abs(p[2] - p[0]) < 0.01})
    ys = sorted({p[1] for p in gray if abs(p[3] - p[1]) < 0.01})
    if len(xs) < 4 or len(ys) < 4:
        raise UnsupportedCondition("the native derivative lattice is unresolved")
    # Merge almost coincident export strokes before measuring the cell pitch.
    from solution_runner.converters.graph_png_to_svg_by_contrast import fit_grid_axis

    ux = fit_grid_axis(xs, max(xs) - min(xs) + 1).step
    uy = fit_grid_axis(ys, max(ys) - min(ys) + 1).step
    segments = []
    for n in root.iter(tangent_native.NS + "path"):
        if n.get("stroke", "").lower() == "#143b8f":
            segments.extend(primitive_svg._segments(n.get("d", "")))
    if not segments:
        raise UnsupportedCondition("one native derivative curve is required")
    left = min(min(s[0, 0], s[-1, 0]) for s in segments)
    right = max(max(s[0, 0], s[-1, 0]) for s in segments)
    domain = ((left - ox) / ux, (right - ox) / ux)
    if q.domain and max(abs(float(a) - b) for a, b in zip(q.domain, domain)) > 0.15:
        raise UnsupportedCondition(
            "the native graph endpoints disagree with the stated domain"
        )
    interval = Interval(*(Fraction(str(x)) for x in domain))
    trace = graph_stationary.Question(
        "count", interval, interval, horizontal=Fraction(q.slope)
    )
    entry = _native_entry(source, trace)
    # The exported horizontal and vertical cells can differ slightly.
    # Intersections use the measured vertical pitch; abscissas use ux separately.
    entry["svg_origin"] = [ox, oy]
    entry["svg_unit"] = uy
    entry["x_unit"] = ux
    for node in entry["curve_nodes"]:
        y = (oy - node["svg"][1]) / uy
        node.pop("y", None)
        node.pop("y_bounds", None)
        if abs(y - round(y)) < 0.04:
            node["y"] = str(round(y))
        else:
            node["y_bounds"] = [str(y - 0.02), str(y + 0.02)]
    return entry


def input(context, data):
    q, condition, asset = read(context)
    model = None
    if (
        data.startswith((raster_primitive.PNG, b"\xff\xd8"))
        or raster_primitive.META.encode() in data
    ):
        if q.domain is None and data.startswith((raster_primitive.PNG, b"\xff\xd8")):
            model = recover_unbounded(data, q)
        else:
            domain = q.domain
            if domain is None:
                import json

                payload = json.loads(
                    ET.fromstring(data)
                    .find(
                        tangent_native.NS
                        + 'metadata[@id="'
                        + raster_primitive.META
                        + '"]'
                    )
                    .text
                )
                domain = tuple(map(float, payload["model"]["domain"]))
            span = Interval(*domain)
            trace = graph_stationary.Question(
                "count", span, span, horizontal=Fraction(q.slope)
            )
            model = (
                raster_primitive.embedded(
                    data.replace("y = f′(x)".encode(), b"y = F(x)"), trace
                )
                if raster_primitive.META.encode() in data
                else deepcopy(shared._recover(data, trace))
            )
        entry = _model_entry(model)
    else:
        entry = native(data, q)
    points = _intersections(entry, q.slope)
    if q.count:
        return q, condition, asset, entry, points, model, str(len(points))
    if not points or (not q.smallest and len(points) != 1):
        raise UnsupportedCondition("the requested abscissa must be uniquely readable")
    point = min(points)
    raw = (point[0] - entry["svg_origin"][0]) / entry.get("x_unit", entry["svg_unit"])
    exact = round(raw)
    if abs(raw - exact) > 0.15:
        raise UnsupportedCondition(
            "the requested abscissa is not resolved at an exact grid coordinate"
        )
    return q, condition, asset, entry, points, model, str(exact)


@lru_cache(maxsize=32)
def recover_unbounded(data, q):
    import io

    import cv2
    from PIL import Image
    from scipy.interpolate import PchipInterpolator

    from solution_runner.converters import graph_png_to_svg_by_contrast as base

    from .derivative_level_curves import fit_logical
    from .derivative_level_trace import _full_path, clean_curve_ink

    image = Image.open(io.BytesIO(data)).convert("RGBA")
    rgba = np.asarray(image)
    dark = base.effective_darkness(rgba)
    grid = base.detect_grid(
        dark,
        foreground_threshold=0.06,
        grid_mask_radius=None,
        vertical_axis_x=None,
        horizontal_axis_y=None,
    )
    ink = clean_curve_ink(dark, grid).astype("uint8")
    yy, xx = np.indices(ink.shape)
    ink[
        (xx < min(grid.vertical.observed) + 2)
        | (xx > max(grid.vertical.observed) - 2)
        | (yy < min(grid.horizontal.observed) + 2)
        | (yy > max(grid.horizontal.observed) - 2)
    ] = 0
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink, 8)
    keep = np.zeros(count, dtype=bool)
    for i in range(1, count):
        _x, y, w, h, _area = stats[i]
        keep[i] = w > 0.65 * grid.vertical.step or h > 0.8 * grid.horizontal.step
    mask = keep[labels]
    ys, xs = np.nonzero(mask)
    if len(xs) < 50:
        raise UnsupportedCondition("the continuous source curve is unresolved")
    left, right = int(xs.min()), int(xs.max())
    lo = (left - grid.vertical_axis_x) / grid.vertical.step
    hi = (right - grid.vertical_axis_x) / grid.vertical.step
    clean = dark.copy()
    clean[~mask] = 0
    rough = _full_path(clean, grid, lo, hi)
    samples = []
    for px, ref in rough:
        px = int(px)
        yy = np.flatnonzero(mask[:, px])
        if not len(yy):
            continue
        groups = np.split(yy, np.flatnonzero(np.diff(yy) > 3) + 1)
        y = min((float(np.median(a)) for a in groups), key=lambda y: abs(y - ref))
        if abs(y - ref) < grid.horizontal.step * 0.3:
            samples.append((px, y))
    samples = np.asarray(samples)
    if len(samples) < 30:
        raise UnsupportedCondition("too little source-supported curve ink")
    xs = np.linspace(samples[0, 0], samples[-1, 0], max(200, len(rough)))
    ys = PchipInterpolator(samples[:, 0], samples[:, 1])(xs)
    logical = np.column_stack(
        (
            (xs - grid.vertical_axis_x) / grid.vertical.step,
            (grid.horizontal_axis_y - ys) / grid.horizontal.step,
        )
    )
    from scipy.ndimage import gaussian_filter1d

    logical[:, 1] = gaussian_filter1d(
        logical[:, 1], 0.1 / np.median(np.diff(logical[:, 0])), mode="nearest"
    )
    span = Interval(float(logical[0, 0]), float(logical[-1, 0]))
    trace = graph_stationary.Question("count", span, span, horizontal=Fraction(q.slope))
    model = fit_logical(
        data,
        trace,
        logical,
        grid,
        {"continuous_plot": True, "clean_ink_components": True},
    )

    model["continuous_plot"] = True
    return model
