"""Recover two straight rays on a unit square grid, without smoothing corners."""

import hashlib
import io
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import cv2
import numpy as np
from PIL import Image

from ...converters import graph_png_to_svg_by_contrast as grid_reader
from ..probability.common import UnsupportedCondition

PNG = b"\x89PNG\r\n\x1a\n"
META = "solution-runner-trapezoid-rays-v1"
NS = "{http://www.w3.org/2000/svg}"


def recover(data, lower, upper):
    image = Image.open(io.BytesIO(data)).convert("RGBA")
    if min(image.size) < 35 or max(image.size) > 5000:
        raise UnsupportedCondition("unsupported ray raster dimensions")
    bg = Image.new("RGBA", image.size, "white")
    bg.alpha_composite(image)
    darkness = grid_reader.effective_darkness(np.asarray(bg))
    vx = grid_reader.projection_line_centers(
        darkness, vertical=True, foreground_threshold=0.2
    )
    hy = grid_reader.projection_line_centers(
        darkness, vertical=False, foreground_threshold=0.2
    )
    vertical = grid_reader.fit_grid_axis(vx, image.width)
    if len(hy) < 3:
        raise UnsupportedCondition(
            "at least three horizontal unit-grid lines are required"
        )
    if len(hy) == 3:
        sy = float(np.median(np.diff(hy)))
        if max(abs(np.diff(hy) - sy)) > sy * 0.05:
            raise UnsupportedCondition("the short grid is not regular")
        xs = vertical.lines(0, image.width - 1)
        ys = tuple(hy)
        ox, oy = vx[0], hy[-1]
        monochrome = True
    else:
        grid = grid_reader.detect_grid(
            darkness,
            foreground_threshold=0.2,
            grid_mask_radius=None,
            vertical_axis_x=None,
            horizontal_axis_y=None,
        )
        vertical = grid.vertical
        sy = grid.horizontal.step
        xs = vertical.lines(0, image.width - 1)
        ys = grid.horizontal.lines(0, image.height - 1)
        # Monochrome originals use the bottom/left unit-grid lines as axes.
        # In the coloured/grey-grid original, contrast independently marks axes.
        samples = [
            darkness[int(round(y)), max(0, int(x) - 2) : int(x) + 3].max()
            for x in vx
            for y in ((hy[0] + hy[1]) / 2, (hy[-1] + hy[-2]) / 2)
        ]
        monochrome = bool(np.median(samples) > 0.8)
        if monochrome:
            ox, oy = (
                vertical.origin,
                grid.horizontal.origin
                + round((hy[-1] - grid.horizontal.origin) / sy) * sy,
            )
        else:
            ox, oy = grid.vertical_axis_x, grid.horizontal_axis_y
    sx = vertical.step
    if not 0.9 < sx / sy < 1.1:
        raise UnsupportedCondition("the source needs a square unit grid")
    yy, xx = np.indices(darkness.shape)
    keep = (darkness > 0.35) & (xx > ox + sx * 0.12) & (yy > hy[0]) & (yy < oy)
    radius = max(1.5, min(sx, sy) * 0.035)
    for x in xs:
        keep &= abs(xx - x) > radius
    for y in ys:
        keep &= abs(yy - y) > radius
    segments = cv2.HoughLinesP(
        keep.astype("uint8") * 255,
        1,
        np.pi / 1800,
        threshold=max(10, int(sx * 0.3)),
        minLineLength=sx * 0.7,
        maxLineGap=sx * 0.35,
    )
    candidates = (
        []
        if segments is None
        else [
            s[0]
            for s in segments
            if abs(s[0][2] - s[0][0]) > sx * 0.3 and abs(s[0][3] - s[0][1]) > sy * 0.3
        ]
    )
    if not candidates:
        raise UnsupportedCondition("one complete diagonal ray is required")
    x1, y1, x2, y2 = max(candidates, key=lambda s: np.hypot(s[2] - s[0], s[3] - s[1]))
    slope = (y2 - y1) / (x2 - x1)
    intercept = y1 - slope * x1
    py, px = np.nonzero(keep)
    for _ in range(3):
        mask = abs(py - slope * px - intercept) < max(2, sx * 0.04)
        if mask.sum() < sx * 0.7:
            raise UnsupportedCondition("insufficient straight ray support")
        slope, intercept = np.polyfit(px[mask], py[mask], 1)
    px, py = px[mask], py[mask]
    rmse = float(np.sqrt(np.mean((py - slope * px - intercept) ** 2)))
    if rmse > max(1.5, sx * 0.025):
        raise UnsupportedCondition("the graph is not a straight ray")
    height = (
        round((oy - hy[0]) / sy) if monochrome else round((oy - float(py.min())) / sy)
    )
    tolerance = min(0.8, 0.13 + abs(slope) * sx / sy * 0.05)
    if not 1 <= height <= 30 or abs((oy - float(py.min())) / sy - height) > tolerance:
        raise UnsupportedCondition(
            f"the corner height is ambiguous: {height}, {(oy - float(py.min())) / sy:.3f}, {monochrome}"
        )
    corner_y = oy - height * sy
    join_float = ((corner_y - intercept) / slope - ox) / sx
    zero_float = ((oy - intercept) / slope - ox) / sx
    join, zero = round(join_float), round(zero_float)
    if max(abs(join - join_float), abs(zero - zero_float)) > 0.15 or join == zero:
        raise UnsupportedCondition("the ray does not meet labelled lattice points")
    rising = join > zero
    if not float(lower) < join < float(upper) or (
        zero != lower if rising else zero != upper
    ):
        raise UnsupportedCondition("the raster ray and question bounds disagree")
    # Diagonal evidence must extend from the top corner to the x-axis.
    if (
        abs(float(py.max()) - oy) > tolerance * sy
        or abs(float(py.min()) - corner_y) > tolerance * sy
    ):
        raise UnsupportedCondition("the diagonal ray is clipped before an endpoint")
    return {
        "height": height,
        "join": join,
        "zero": zero,
        "rising": rising,
        "span": [str(lower), str(upper)],
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "source_frame": {
            "origin": [float(ox), float(oy)],
            "units": [float(sx), float(sy)],
            "fit_rmse_pixels": rmse,
        },
    }


def render(model, *, shaded=False):
    """Use the group's original SVG style; a shaded copy shares all geometry."""
    h, c, z = model["height"], model["join"], model["zero"]
    lower, upper = map(float, model["span"])
    cell = 20.0
    xmin = -2
    xmax = max(c, z, upper) + 2
    ymax = h + 2
    ymin = -2
    width = (xmax - xmin) * cell
    height = (ymax - ymin) * cell
    ox = -xmin * cell
    oy = ymax * cell
    point = lambda x, y: (ox + x * cell, oy - y * cell)
    template = ET.parse(
        Path(__file__).with_name("assets") / "trapezoid-rays-template.svg"
    ).getroot()
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
    ET.SubElement(root, "metadata", {"id": META}).text = json.dumps(
        {"model": model, "shaded": shaded}, sort_keys=True
    )
    for x in range(xmin, int(xmax) + 1):
        attrs = {
            k: v
            for k, v in template[0].attrib.items()
            if k not in ("x1", "x2", "y1", "y2")
        }
        px = point(x, 0)[0]
        ET.SubElement(
            root,
            "line",
            {**attrs, "x1": str(px), "x2": str(px), "y1": "0", "y2": str(height)},
        )
    for y in range(ymin, int(ymax) + 1):
        py = point(0, y)[1]
        ET.SubElement(
            root,
            "line",
            {**attrs, "x1": "0", "x2": str(width), "y1": str(py), "y2": str(py)},
        )
    if shaded:
        top = (
            [point(lower, h), point(c, h), point(upper, 0)]
            if not model["rising"]
            else [point(lower, 0), point(c, h), point(upper, h)]
        )
        vertices = [point(lower, 0), *top, point(upper, 0)]
        ET.SubElement(
            root,
            "polygon",
            {
                "id": "integral-area",
                "points": " ".join(f"{x},{y}" for x, y in vertices),
                "fill": "#143B8F",
                "fill-opacity": "0.5",
            },
        )
    horizontal, vertical = template[30], template[32]
    horizontal.set("y1", str(oy))
    horizontal.set("y2", str(oy))
    horizontal.set("x2", str(width - 3))
    vertical.set("x1", str(ox))
    vertical.set("x2", str(ox))
    vertical.set("y1", str(height))
    root.extend((horizontal, vertical))
    # Clip at the diagram boundary, leaving the diagonal as a genuine ray.
    end_x = z + (ymin * (c - z) / h)
    start_x = xmin if not model["rising"] else min(c, end_x)
    end_x = max(c, end_x) if not model["rising"] else xmax
    coords = (
        [point(xmin, h), point(c, h), point(end_x, ymin)]
        if not model["rising"]
        else [point(start_x, ymin), point(c, h), point(xmax, h)]
    )
    curve_attrs = {
        k: v
        for k, v in template[40].attrib.items()
        if k not in ("x1", "x2", "y1", "y2")
    }
    for first, last in zip(coords, coords[1:]):
        ET.SubElement(
            root,
            "line",
            {
                **curve_attrs,
                "data-ray-segment": "true",
                "x1": str(first[0]),
                "y1": str(first[1]),
                "x2": str(last[0]),
                "y2": str(last[1]),
            },
        )
    bound = upper if model["rising"] else lower
    px = point(bound, 0)[0]
    guide = {
        k: v
        for k, v in template[42].attrib.items()
        if k not in ("x1", "x2", "y1", "y2")
    }
    ET.SubElement(
        root,
        "line",
        {
            **guide,
            "x1": str(px),
            "x2": str(px),
            "y1": str(oy),
            "y2": str(point(bound, h)[1]),
        },
    )
    # Copy the exact outlined O/x/y labels and arrows from the group's parent.
    for index, dx, dy in [
        (37, ox - 40.488, oy - 80.367),
        (38, ox - 40.488, 0),
        (39, width - 240.051, oy - 80.367),
        (22, width - 240.051, oy - 80.4469),
        (31, ox - 40.482, -0.4159),
    ]:
        node = template[index]
        node.set("transform", f"translate({dx} {dy})")
        root.append(node)
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
        rx = x - w / 2 if anchor == "middle" else x - w
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

    for x in sorted({1.0, lower, upper, float(c), float(z)} - {0.0}):
        label(point(x, 0)[0], oy + 14, f"{x:g}")
    for y in sorted({1, h}):
        label(ox - 5, point(0, y)[1] + 5, y, "end")
    return ET.tostring(root, encoding="unicode")


def embedded(data, lower, upper):
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    node = root.find(NS + 'metadata[@id="' + META + '"]')
    if node is None:
        return None
    payload = json.loads(node.text)
    model = payload["model"]
    if payload["shaded"] or render(model).encode() != data:
        raise UnsupportedCondition("the prepared ray SVG has changed")
    if model["span"] != [str(lower), str(upper)]:
        raise UnsupportedCondition("the SVG interval and question bounds disagree")
    return model
