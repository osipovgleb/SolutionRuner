"""Inspect visible markers using independently reviewed pi/4 and half-unit grids."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import sympy as sp
from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import _normalized_content
from .explog_svg import distance
from .linear_svg import NS, frame, snap
from .parabola_svg import curves

ASSET_DIR = Path(__file__).parent / "assets/trig"


def read(context, data, mime, function):
    content = _normalized_content(context)
    if len(content["assets"]) != 1 or any(
        s.get("asset_keys")
        or BeautifulSoup(s.get("html", ""), "html.parser").select(
            "img, [data-asset-key], [data-asset-id]"
        )
        for s in content["sections"]
        if s.get("key") != "condition"
    ):
        raise ContentPlanError(
            "the trigonometric methods use only the original condition figure"
        )
    if not data or str(mime).split(";")[0].lower() != "image/svg+xml":
        raise ContentPlanError("one inspected trigonometric SVG is required")
    entry = json.loads((ASSET_DIR / "source-evidence.json").read_text()).get(
        hashlib.sha256(data).hexdigest()
    )
    if (
        not entry
        or entry["grid_unit"] != ["pi/4", "1/2"]
        or entry["function"] != function
        or entry["grid_color"] not in {"#ADAAAA", "#C0BFBF"}
    ):
        raise ContentPlanError(
            "the graph function, exact bytes and coordinate units need inspection"
        )
    root = ET.fromstring(data)
    axes = frame(root, grid_color=entry["grid_color"])
    xmap, ymap, sx, sy = axes
    paths = curves(root)
    if set(paths) != {"#143B8F"}:
        raise ContentPlanError("one inspected blue trigonometric graph is required")
    left, top, width, height = map(float, root.get("viewBox").split())
    inside = []
    outside = 0
    for marker in root.iter(NS + "circle"):
        cx, cy = float(marker.get("cx")), float(marker.get("cy"))
        if not left <= cx <= left + width or not top <= cy <= top + height:
            outside += 1
            continue
        if marker.get("fill", "").upper() != "#143B8F":
            raise ContentPlanError(
                "all visible graph markers must have the inspected blue color"
            )
        inside.append((snap(cx, xmap, sx), snap(cy, ymap, sy)))
    if (
        not inside
        or len(set(inside)) != len(inside)
        or outside != entry["outside_marker_count"]
    ):
        raise ContentPlanError(
            "visible markers and clipped export artifacts must match inspection"
        )
    points = inside + [tuple(p) for p in entry["read_points"]]
    if any(distance(p, paths["#143B8F"], axes) > 0.2 for p in points):
        raise ContentPlanError(
            "all inspected grid readings must lie on the original curve"
        )
    return sorted({(sp.Rational(x, 4) * sp.pi, sp.Rational(y, 2)) for x, y in points})
