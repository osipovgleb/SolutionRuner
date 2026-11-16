"""Recover a shaded raster parabola against the exact stated primitive.

No answer is used to infer the diagram. Ambiguous axes, curvature, or integration
bounds are rejected; accepted diagrams are rebuilt as exact quadratic SVG paths.
"""

import hashlib
import io
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import sympy as sp
from PIL import Image
from scipy.ndimage import median_filter
from scipy.optimize import least_squares

from ..probability.common import UnsupportedCondition
from .common import X

PNG = b"\x89PNG\r\n\x1a\n"
NS = "{http://www.w3.org/2000/svg}"
META = "solution-runner-parabola-v1"


def recover(data, primitive):
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    bg = Image.new("RGBA", image.size, "white")
    bg.alpha_composite(image)
    gray = np.asarray(bg.convert("L"))
    height, width = gray.shape
    if min(height, width) < 35 or max(height, width) > 5000:
        raise UnsupportedCondition("unsupported parabola raster dimensions")
    p = sp.Poly(sp.diff(primitive, X), X)
    if p.degree() != 2 or not all(c.is_Rational for c in p.all_coeffs()):
        raise UnsupportedCondition("a rational quadratic derivative is required")
    a, b, _c = p.all_coeffs()
    center = -b / (2 * a)
    vertex = p.as_expr().subs(X, center)
    if vertex <= 0:
        raise UnsupportedCondition("the raster parabola needs a positive vertex")
    dark = gray < 210
    row_strength = dark.sum(axis=1).astype(float)
    row_strength[: height // 3] = 0
    row_strength[int(height * 0.97) :] = 0
    oy = int(np.argmax(row_strength))
    if row_strength[oy] < width * 0.65:
        raise UnsupportedCondition("a complete horizontal axis is required")
    # Broad filled columns distinguish the shaded region from thin axes/labels.
    support = dark[3 : max(4, oy - 3)].sum(axis=0)
    mask = support > 5
    runs = []
    start = None
    for x, yes in enumerate(np.r_[mask, False]):
        if yes and start is None:
            start = x
        if not yes and start is not None:
            if x - start > width * 0.07:
                runs.append((start, x - 1))
            start = None
    if not runs:
        raise UnsupportedCondition("a bounded shaded region is required")
    left, right = max(runs, key=lambda r: r[1] - r[0])
    points = []
    for x in range(left + 2, right - 1):
        ys = np.flatnonzero(dark[2 : oy - 2, x]) + 2
        if len(ys) > 4:
            points.append((x, float(ys[0])))
    points = np.array(points)
    if len(points) < 12:
        raise UnsupportedCondition("the shaded curve is incomplete")
    # Clipped upper portions are excluded from fitting.
    points = points[(points[:, 1] > 4) & (points[:, 1] < oy - 3)]
    if len(points) < 12:
        raise UnsupportedCondition("the parabola vertex is clipped")
    values = median_filter(points[:, 1], size=3)
    xmid = float(points[:, 0].mean())
    xscale = float(np.ptp(points[:, 0]))
    xx = (points[:, 0] - xmid) / xscale
    seed = np.polyfit(xx, values, 2)
    fit = least_squares(
        lambda coeff: np.polyval(coeff, xx) - values, seed, loss="soft_l1", f_scale=1.0
    )
    keep = np.abs(np.polyval(fit.x, xx) - values) < 3
    if keep.sum() < 12:
        raise UnsupportedCondition("too few curve samples survive label rejection")
    fitted = np.polyfit(xx[keep], values[keep], 2)
    coef = np.array(
        [
            fitted[0] / xscale**2,
            fitted[1] / xscale - 2 * fitted[0] * xmid / xscale**2,
            fitted[2] - fitted[1] * xmid / xscale + fitted[0] * xmid * xmid / xscale**2,
        ]
    )
    if coef[0] * float(a) >= 0:
        raise UnsupportedCondition("raster and formula curvature disagree")
    vx = -coef[1] / (2 * coef[0])
    vy = float(np.polyval(coef, vx))
    sy = (oy - vy) / float(vertex)
    if sy <= 0:
        raise UnsupportedCondition("invalid positive parabola scale")
    sx = math.sqrt(abs(sy * float(a) / coef[0]))
    ox = vx - sx * float(center)
    if a < 0:
        formula_roots = sorted(sp.solve(p.as_expr(), X))
        pixel_roots = sorted(np.roots([coef[0], coef[1], coef[2] - oy]))
        if len(formula_roots) != 2 or not all(r.is_Rational for r in formula_roots):
            raise UnsupportedCondition("the shaded cap needs exact rational zeroes")
        sx = float(
            (pixel_roots[1] - pixel_roots[0])
            / float(formula_roots[1] - formula_roots[0])
        )
        ox = float(pixel_roots[0] - sx * float(formula_roots[0]))
    residual = float(
        np.sqrt(np.mean((np.polyval(coef, points[keep, 0]) - points[keep, 1]) ** 2))
    )
    if residual > max(2.0, oy * 0.025) or sx < 3:
        raise UnsupportedCondition("the raster does not resolve a unique parabola")
    # Require an independently visible vertical axis near the recovered origin.
    vertical = dark[3 : oy + 1].sum(axis=0)
    below = dark[min(height, oy + 3) :].sum(axis=0)
    candidates = np.flatnonzero((vertical > oy * 0.40) & (below >= 4))
    candidates = candidates[(candidates > 1) & (candidates < width - 2)]
    if len(candidates) == 0:
        raise UnsupportedCondition("the raster needs a visible vertical axis")
    visible = int(candidates[np.argmin(abs(candidates - ox))])
    if vertical[visible] < oy * 0.40 or abs(visible - ox) > max(5, sx * 0.35):
        raise UnsupportedCondition(
            "the recovered origin disagrees with the visible axis"
        )
    if center != 0:
        axis_scale = (vx - visible) / float(center)
        if axis_scale <= 0 or abs(axis_scale / sx - 1) > 0.30:
            raise UnsupportedCondition("the axis and curvature scales disagree")
        sx = axis_scale
        ox = visible
    span = []
    if a < 0:
        roots = sp.solve(p.as_expr(), X)
        if len(roots) != 2 or any(r.is_Rational is not True for r in roots):
            raise UnsupportedCondition("the shaded cap needs exact rational zeroes")
        span = sorted(roots)
        pixel_roots = sorted(np.roots([coef[0], coef[1], coef[2] - oy]))
        if (
            max(
                abs((pixel_roots[0] - ox) / sx - float(span[0])),
                abs((pixel_roots[1] - ox) / sx - float(span[1])),
            )
            > 0.22
        ):
            raise UnsupportedCondition(
                "the shaded cap does not end at its formula zeroes"
            )
    else:
        for pixel in (left, right):
            value = (pixel - ox) / sx
            snapped = round(value * 2) / 2
            if abs(value - snapped) > 0.16:
                raise UnsupportedCondition(
                    "the shading boundary is ambiguous on the half-unit lattice"
                )
            span.append(sp.Rational(str(snapped)))
    return {
        "coefficients": [str(n) for n in p.all_coeffs()],
        "span": [str(n) for n in span],
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "source_frame": {
            "origin": [ox, oy],
            "units": [sx, sy],
            "fit_rmse_pixels": residual,
        },
    }


def render(model):
    """Adapt the reviewed 323383 SVG, preserving its actual drawing elements.

    The source supplies curve/fill styles, axes, arrow polygons and outlined
    O/x/y glyphs. Only geometry and numerical endpoint labels are regenerated.
    """
    a, b, c = map(sp.Rational, model["coefficients"])
    left, right = map(sp.Rational, model["span"])
    f = a * X**2 + b * X + c
    center = -b / (2 * a)
    peak = float(f.subs(X, center))
    xmin = min(float(left) - 0.6, -0.8)
    xmax = max(float(right) + 1.25, 1.1)
    width = max(220.0, (xmax - xmin) * 30.0)
    sx = width / (xmax - xmin)
    ox = -xmin * sx
    oy = 120.512
    ymax = max(peak, float(f.subs(X, left)), float(f.subs(X, right)))
    sy = (oy - 18.93) / ymax
    near_origin = any(0 < abs(float(x) * sx) < 28 for x in (left, right))
    origin_label_dy = 18 if near_origin else 0
    height = 139.4046 + origin_label_dy

    def point(x, y):
        return ox + float(x) * sx, oy - float(y) * sy

    def quadratic(lo, hi):
        x0, y0 = point(lo, f.subs(X, lo))
        x2, y2 = point(hi, f.subs(X, hi))
        x1 = (x0 + x2) / 2
        y1 = y0 - float(sp.diff(f, X).subs(X, lo)) * float(hi - lo) * sy / 2
        return f"M{x0:.5f} {y0:.5f} Q{x1:.5f} {y1:.5f} {x2:.5f} {y2:.5f}"

    path = quadratic(left, right)
    lo, hi = point(left, 0), point(right, 0)
    area = path + f"L{hi[0]:.5f} {oy} L{lo[0]:.5f} {oy} Z"
    whole = path if a < 0 else quadratic(sp.Rational(str(xmin)), sp.Rational(str(xmax)))
    entry = {
        "curve_name": "f",
        "integral_model": "quadratic",
        "area_kind": "bowl" if a > 0 else "cap",
        "area_span": [str(left), str(right)],
        "area_svg_span": [lo[0], hi[0]],
        "derivative_coefficients": [str(a), str(b), str(c)],
        "svg_origin": [ox, oy],
        "svg_units": [sx, sy],
        "area_methods": "endpoints",
        "raster_recovered": True,
    }
    # Exact quadratic represented as one cubic for the existing mathematical reader.
    p0 = point(left, f.subs(X, left))
    p3 = point(right, f.subs(X, right))
    dx = float(right - left) * sx
    entry["curve_segments"] = [
        [
            list(p0),
            [
                p0[0] + dx / 3,
                p0[1]
                - float(sp.diff(f, X).subs(X, left)) * float(right - left) * sy / 3,
            ],
            [
                p3[0] - dx / 3,
                p3[1]
                + float(sp.diff(f, X).subs(X, right)) * float(right - left) * sy / 3,
            ],
            list(p3),
        ]
    ]
    metadata = json.dumps({"model": model, "entry": entry}, sort_keys=True)
    template = ET.parse(
        Path(__file__).with_name("assets") / "parabola-area-template.svg"
    ).getroot()
    # Unqualified construction with one explicit xmlns stays deterministic even
    # when another converter has changed ElementTree's process-wide registry.
    for element in template.iter():
        element.tag = element.tag.rsplit("}", 1)[-1]
        href = element.attrib.pop("{http://www.w3.org/1999/xlink}href", None)
        if href is not None:
            element.set("xlink:href", href)
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
    ET.SubElement(root, "metadata", {"id": META}).text = metadata
    defs = ET.SubElement(root, "defs")
    clip = ET.SubElement(defs, "clipPath", {"id": "plot"})
    ET.SubElement(clip, "rect", {"width": str(width), "height": str(oy)})
    plot = ET.SubElement(root, "g", {"clip-path": "url(#plot)"})
    shade, curve = template[0], template[1]
    shade.set("d", area)
    curve.set("d", whole)
    plot.extend((shade, curve))
    if a > 0:
        ET.SubElement(
            plot,
            "path",
            {
                "d": f"M{lo[0]} {oy}V{point(left, f.subs(X, left))[1]} "
                f"M{hi[0]} {oy}V{point(right, f.subs(X, right))[1]}",
                "fill": "none",
                "stroke": "#000000",
                "stroke-width": "1",
                "stroke-dasharray": "7.5,3",
            },
        )
    horizontal, vertical = template[2], template[3]
    horizontal.set("x2", str(width - 5.3835))
    vertical.set("x1", str(ox))
    vertical.set("x2", str(ox))
    vertical.set("y1", str(height))
    root.extend((horizontal, vertical))
    # These are the original outlined glyphs, so the template's O never
    # becomes a centered zero crossing the vertical axis.
    origin, y_label, x_label = template[7], template[8], template[9]
    origin.set("id", "origin-label")
    origin.set("transform", f"translate({ox - 317.1145} {origin_label_dy})")
    y_label.set("transform", f"translate({ox - 317.1145} 0)")
    x_label.set("transform", f"translate({width - 354.1575} 0)")
    root.extend((origin, y_label, x_label))
    labels = ET.SubElement(
        root,
        "g",
        {
            "id": "endpoint-labels",
            "fill": "#000000",
            "font-family": "Times New Roman, Times, serif",
            "font-size": "15",
        },
    )
    for x in sorted({left, right} - {sp.Integer(0)}):
        label = ET.SubElement(
            labels,
            "text",
            {"x": str(point(x, 0)[0]), "y": str(oy + 14), "text-anchor": "middle"},
        )
        label.text = str(x).replace("-", "−")
    right_arrow, top_arrow = template[10], template[11]
    right_arrow.set("transform", f"translate({width - 354.1575} 0)")
    top_arrow.set("transform", f"translate({ox - 317.1145} 0)")
    root.extend((right_arrow, top_arrow))
    return ET.tostring(root, encoding="unicode"), entry


def embedded(data, primitive):
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    node = root.find(NS + 'metadata[@id="' + META + '"]')
    if node is None:
        return None
    payload = json.loads(node.text)
    svg, entry = render(payload["model"])
    if svg.encode() != data:
        raise UnsupportedCondition(
            "the generated parabola SVG changed after preparation"
        )
    actual = [str(n) for n in sp.Poly(sp.diff(primitive, X), X).all_coeffs()]
    if actual != entry["derivative_coefficients"]:
        raise UnsupportedCondition(
            "the generated parabola disagrees with the current primitive"
        )
    return entry
