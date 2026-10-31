"""Read audited graph markers and verify extra lattice readings on native curves."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import sympy as sp
from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import _normalized_content
from .linear_svg import NS, frame
from .parabola_svg import curves, pixel

ASSET_DIR = Path(__file__).parent / "assets/explog"


def coordinate(position, mapping, step, denominator):
    sign = 1 if mapping[-1][1] > mapping[0][1] else -1
    near, value = min(mapping, key=lambda p: abs(p[0] - position))
    exact = sp.Rational(
        round(denominator * (value + sign * (position - near) / step)), denominator
    )
    if abs(pixel(exact, mapping) - position) >= step * 0.075:
        raise ContentPlanError("the marker must identify one inspected grid coordinate")
    return exact


def distance(point, curve, axes):
    xmap, ymap, sx, sy = axes
    sought = np.array([pixel(point[0], xmap), pixel(point[1], ymap)])
    t = np.linspace(0, 1, 2001)[:, None]
    nearest = []
    for p in map(np.asarray, curve):
        samples = (
            (1 - t) ** 3 * p[0]
            + 3 * (1 - t) ** 2 * t * p[1]
            + 3 * (1 - t) * t**2 * p[2]
            + t**3 * p[3]
        )
        nearest.append(np.linalg.norm((samples - sought) / [sx, sy], axis=1).min())
    return min(nearest)


def read(context, data, mime, model):
    content = _normalized_content(context)
    if len(content["assets"]) != 1 or any(
        s.get("asset_keys")
        or BeautifulSoup(s.get("html", ""), "html.parser").select(
            "img, [data-asset-id], [data-asset-key]"
        )
        for s in content["sections"]
        if s.get("key") != "condition"
    ):
        raise ContentPlanError(
            "the graph methods use only the original condition figure"
        )
    if not data or str(mime).split(";")[0].lower() != "image/svg+xml":
        raise ContentPlanError(
            "an inspected exponential or logarithmic SVG is required"
        )
    entry = json.loads((ASSET_DIR / "source-evidence.json").read_text()).get(
        hashlib.sha256(data).hexdigest()
    )
    if not entry or entry["grid_unit"] != [1, 1] or model not in entry["models"]:
        raise ContentPlanError(
            "the graph model, exact bytes and grid units need inspection"
        )
    root = ET.fromstring(data)
    axes = frame(root)
    xmap, ymap, sx, sy = axes
    paths = curves(root)
    markers = list(root.iter(NS + "circle"))
    if (
        set(paths) != {"#143B8F"}
        or not markers
        or any(m.get("fill", "").upper() != "#143B8F" for m in markers)
    ):
        raise ContentPlanError(
            "one inspected blue curve with marked points is required"
        )
    denominator = entry["marker_denominator"]
    if denominator not in (1, 2):
        raise ContentPlanError(
            "only inspected integer and half-integer markers are supported"
        )
    marked = [
        tuple(
            coordinate(float(m.get(k)), mapping, step, denominator)
            for k, mapping, step in (("cx", xmap, sx), ("cy", ymap, sy))
        )
        for m in markers
    ]
    if len(set(marked)) != len(marked):
        raise ContentPlanError("duplicate graph markers are ambiguous")
    points = marked + [tuple(map(sp.Rational, p)) for p in entry["read_points"]]
    if any(distance(p, paths["#143B8F"], axes) > 0.2 for p in points):
        raise ContentPlanError("an inspected coordinate must lie on the original curve")
    return entry, sorted(set(points)), marked
