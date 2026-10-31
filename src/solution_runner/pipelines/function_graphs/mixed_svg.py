"""Exact original figures, inspected coordinates, native paths and one PNG grid."""

import hashlib
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
from PIL import Image

from ..core.errors import ContentPlanError
from ..triangles.isosceles.planner import _normalized_content
from .explog_svg import distance
from .linear_svg import NS, frame, snap
from .parabola_svg import segments, straight

ASSET_DIR = Path(__file__).parent / "assets/mixed"


def native(root, color):
    result = [
        s
        for n in root.iter(NS + "path")
        if n.get("stroke", "").upper() == color
        for s in segments(n.get("d", ""))
    ]
    for node in root.iter(NS + "line"):
        if node.get("stroke", "").upper() == color:
            p, q = [
                tuple(float(node.get(axis + str(i))) for axis in ("x", "y"))
                for i in (1, 2)
            ]
            result.append(straight(p, q))
    if not result:
        raise ContentPlanError("the inspected colored curve or line is absent")
    return result


def raster(data, entry):
    im = Image.open(io.BytesIO(data)).convert("RGB")
    f = entry["raster_frame"]
    if list(im.size) != f["size"]:
        raise ContentPlanError("the inspected PNG dimensions must match")
    ox, oy = f["origin"]
    sx, sy = f["step"]
    for x, y in entry["curve_points"] + entry["line_points"]:
        px, py = round(ox + sx * x), round(oy - sy * y)
        if not 3 <= px < im.width - 3 or not 3 <= py < im.height - 3:
            raise ContentPlanError(
                "an inspected PNG point must remain inside the figure"
            )
        if not any(
            max(im.getpixel((i, j))) < 80
            for i in range(px - 3, px + 4)
            for j in range(py - 3, py + 4)
        ):
            raise ContentPlanError(
                "an inspected PNG reading must coincide with original dark ink"
            )
    return []


def svg(data, entry):
    root = ET.fromstring(data)
    axes = frame(root, grid_color=entry["grid_color"])
    for key, color in (
        ("curve_points", entry["curve_color"]),
        ("line_points", entry["line_color"]),
    ):
        curve = native(root, color)
        if any(distance(p, curve, axes) > 0.2 for p in entry[key]):
            raise ContentPlanError(
                "an inspected reading must lie on its original colored graph"
            )
    left, top, width, height = map(float, root.get("viewBox").split())
    xmap, ymap, sx, sy = axes
    marked = []
    for m in root.iter(NS + "circle"):
        x, y = float(m.get("cx")), float(m.get("cy"))
        if left <= x <= left + width and top <= y <= top + height:
            color = m.get("fill", "").upper()
            if color not in {entry["curve_color"], entry["line_color"]}:
                raise ContentPlanError(
                    "all visible markers must belong to an inspected graph color"
                )
            marked.append((snap(x, xmap, sx), snap(y, ymap, sy), color))
    return marked


def read(context, data, mime, kind):
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
            "the mixed methods use only the original condition figure"
        )
    entry = json.loads((ASSET_DIR / "source-evidence.json").read_text()).get(
        hashlib.sha256(data or b"").hexdigest()
    )
    if (
        not entry
        or entry["grid_unit"] != [1, 1]
        or entry["kind"] != kind
        or str(mime).split(";")[0].lower() != entry["content_type"]
    ):
        raise ContentPlanError(
            "the exact figure, model, MIME and coordinate units need inspection"
        )
    marked = (
        raster(data, entry)
        if entry["content_type"] == "image/png"
        else svg(data, entry)
    )
    return entry, marked
