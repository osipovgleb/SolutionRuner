"""Convert tangent PNGs during ordinary runs and solve from their lattice."""

import hashlib
import json
import math
import re
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from functools import lru_cache
from html import escape
from xml.etree import ElementTree as ET

import numpy as np
from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition, normalize, rewrite
from ..triangles.right.basic_parent import _targeted
from . import graph_input, graph_tangents, tangent_native, tangent_slope_trace

KEY = "tangent_triangle"
ALT = graph_input.ALT
NS = "{http://www.w3.org/2000/svg}"


def _read(context):
    content = context["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    if len(condition.get("asset_keys", [])) != 1:
        raise UnsupportedCondition(
            "one visible function and tangent diagram is required"
        )
    asset = next(
        a for a in content["assets"] if a["asset_key"] == condition["asset_keys"][0]
    )
    allowed = set(condition["asset_keys"]) | {KEY}
    for section in content["sections"]:
        if section["key"] == "solution":
            allowed.update(section.get("asset_keys", []))
    if any(a["asset_key"] not in allowed for a in content["assets"]):
        raise UnsupportedCondition("an unrelated tangent asset is present")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) != 1 or images[0].get("data-asset-id") != asset["asset_id"]:
        raise UnsupportedCondition("the visible tangent image must match its asset")
    images[0].decompose()
    clean = deepcopy(context)
    clean["normalized_content"]["assets"] = []
    c = next(
        s for s in clean["normalized_content"]["sections"] if s["key"] == "condition"
    )
    c["html"], c["asset_keys"] = str(soup), []
    text = normalize(graph_input._read_text(clean)[4])
    text = text.replace(
        "график функции f(x)и касательная к этому графику, проведенная в точке x_0.",
        "график функции y=f(x)и касательная к нему в точке с абсциссой x_0.",
    )
    text = re.sub(r"x_0\s+\.", "x_0.", text)
    text = text.replace("касательная к нему к точке", "касательная к нему в точке")
    text = text.replace(
        "Дан график функции y=f(x), касательная в точке с абсциссой x_0. Найти значение производной функции f(x)в x_0.",
        "На рисунке изображен график функции y=f(x)и касательная к нему в точке с абсциссой x_0. Найдите значение производной функции f(x)в точке x_0.",
    )
    if not graph_tangents._QUESTION.fullmatch(text):
        raise UnsupportedCondition("the complete tangent slope question is required")
    return condition, asset


def required_assets(context):
    _read(context)
    return ()


def _entry(k, b, origin, unit, bounds, markers=()):
    k = Fraction(k).limit_denominator(10)
    b = Fraction(round(float(b) * k.denominator), k.denominator)
    xmin, ymin, xmax, ymax = bounds
    points = [
        (Fraction(x), k * x + b)
        for x in range(math.ceil(xmin + 0.25), math.floor(xmax - 0.25) + 1)
        if (k * x + b).denominator == 1 and ymin + 0.3 < float(k * x + b) < ymax - 0.3
    ]
    if len(points) < 2:
        raise UnsupportedCondition(
            "two visible exact lattice points on the tangent are required"
        )
    marked = [
        p
        for p in points
        if any(
            np.linalg.norm(np.array(list(map(float, p))) - q) < 0.01 for q in markers
        )
    ]
    p, q = (marked[0], marked[-1]) if len(marked) >= 2 else (points[0], points[-1])
    entry = {
        "vertices": {
            "A": list(map(str, q)),
            "B": [str(q[0]), str(p[1])],
            "C": list(map(str, p)),
        },
        "line_points": [list(map(str, p)), list(map(str, q))],
        "svg_origin": origin,
        "svg_unit": unit,
    }
    graph_tangents.model(entry)
    return entry


def _native(data):
    try:
        return _native_model(data)
    except UnsupportedCondition:
        return _native_model(tangent_native.presentation(data), expanded=True)


def _native_model(data, *, expanded=False):
    root = ET.fromstring(data)
    if any(n.get("transform") for n in root.iter()):
        raise UnsupportedCondition(
            "transformed native tangent coordinates require an audit"
        )
    lines = []
    for n in root.iter(NS + "line"):
        lines.append((n, tuple(float(n.get(k, "0")) for k in ("x1", "y1", "x2", "y2"))))
    if expanded:
        lines = tangent_native.straight_segments(root)
    black = [
        p
        for n, p in lines
        if n.get("stroke", "").lower()
        in ("black", "#000000", "#000", *(("#111", "#010202") if expanded else ()))
    ]
    horizontal = [p for p in black if abs(p[3] - p[1]) < 0.3 and abs(p[2] - p[0]) > 20]
    vertical = [p for p in black if abs(p[2] - p[0]) < 0.3 and abs(p[3] - p[1]) > 20]
    if not horizontal or not vertical:
        raise UnsupportedCondition("native tangent axes are required")
    ox = max(vertical, key=lambda p: abs(p[3] - p[1]))[0]
    oy = max(horizontal, key=lambda p: abs(p[2] - p[0]))[1]
    gray = [
        p
        for n, p in lines
        if n.get("stroke", "").lower() in ("#adadad", "#b2b2b2", "#b3b3b3", "#999999")
    ]
    # Authoring exports also use rgb gray names; select repeated thin axis-aligned
    # strokes by color, never the function or the green tangent.
    if len(gray) < 6:
        colors = {n.get("stroke", "") for n, p in lines if n.get("stroke")}
        groups = [
            [
                p
                for n, p in lines
                if n.get("stroke") == c
                and (abs(p[2] - p[0]) < 0.01 or abs(p[3] - p[1]) < 0.01)
            ]
            for c in colors
            if c.lower() not in ("black", "#000", "#000000", "#0a990a")
        ]
        gray = max(groups, key=len, default=[])
    xs = sorted({p[0] for p in gray if abs(p[2] - p[0]) < 0.01})
    ys = sorted({p[1] for p in gray if abs(p[3] - p[1]) < 0.01})
    if len(xs) < 4 or len(ys) < 4:
        raise UnsupportedCondition("the native graph lattice is unresolved")
    ux, uy = float(np.median(np.diff(xs))), float(np.median(np.diff(ys)))
    if expanded:
        from solution_runner.converters.graph_png_to_svg_by_contrast import (
            fit_grid_axis,
        )

        ux = fit_grid_axis(xs, max(xs) - min(xs) + 1).step
        uy = fit_grid_axis(ys, max(ys) - min(ys) + 1).step
    green = [
        p
        for n, p in lines
        if n.get("stroke", "").lower() == "#0a990a" and abs(p[2] - p[0]) > 3
    ]
    if not green:
        if expanded:
            green = [
                p
                for n, p in lines
                if abs(p[2] - p[0]) > ux * 2
                and abs(p[3] - p[1]) > uy * 0.2
                and not n.get("stroke-dasharray")
                and n.get("stroke", "none") != "none"
            ]
        if not green:
            raise UnsupportedCondition("one native straight tangent is required")
    p = max(green, key=lambda p: math.hypot(p[2] - p[0], p[3] - p[1]))
    rawk = -(p[3] - p[1]) / (p[2] - p[0]) * ux / uy
    rawb = (oy - (p[1] + (ox - p[0]) * (p[3] - p[1]) / (p[2] - p[0]))) / uy
    k = Fraction(rawk).limit_denominator(10)
    b = Fraction(round(rawb * k.denominator), k.denominator)
    if abs(float(k) - rawk) > 0.025 or abs(float(b) - rawb) > 0.13:
        raise UnsupportedCondition(
            "native tangent does not resolve to exact lattice coordinates"
        )
    bounds = (
        (xs[0] - ox) / ux,
        (oy - ys[-1]) / uy,
        (xs[-1] - ox) / ux,
        (oy - ys[0]) / uy,
    )
    return _entry(k, b, [ox, oy], [ux, uy], bounds)


@lru_cache(maxsize=100)
def recover(data):
    if not isinstance(data, bytes):
        raise UnsupportedCondition("downloaded tangent image bytes are required")
    if data.startswith(b"\x89PNG"):
        try:
            svg, g, t, markers, origin = tangent_slope_trace.extract(data)
        except ValueError as e:
            raise UnsupportedCondition(str(e)) from e
        bounds = (
            (g.vertical_lines()[0] - g.vertical_axis_x) / g.vertical.step,
            (g.horizontal_axis_y - g.horizontal_lines()[-1]) / g.horizontal.step,
            (g.vertical_lines()[-1] - g.vertical_axis_x) / g.vertical.step,
            (g.horizontal_axis_y - g.horizontal_lines()[0]) / g.horizontal.step,
        )
        entry = _entry(
            t.logical_slope, t.logical_intercept, origin, [20, 20], bounds, markers
        )
        root = ET.fromstring(svg)
        body_sha256 = hashlib.sha256(ET.tostring(root)).hexdigest()
        meta = ET.SubElement(root, NS + "metadata", {"id": "runner-tangent-model"})
        meta.text = json.dumps(
            {
                "source_sha256": hashlib.sha256(data).hexdigest(),
                "entry": entry,
                "body_sha256": body_sha256,
            },
            sort_keys=True,
        )
        svg = ET.tostring(root, encoding="unicode")
        return svg, entry, True
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise UnsupportedCondition(
            "the downloaded diagram must be a PNG or native SVG tangent diagram"
        ) from e
    meta = root.find(NS + "metadata[@id='runner-tangent-model']")
    if meta is not None:
        metadata = json.loads(meta.text)
        root.remove(meta)
        if metadata.get("body_sha256") != hashlib.sha256(ET.tostring(root)).hexdigest():
            raise UnsupportedCondition(
                "the converted tangent SVG changed after preparation"
            )
        entry = metadata["entry"]
        graph_tangents.model(entry)
        return data.decode(), entry, False
    return data.decode(), _native(data), False


def _solution(svg, entry):
    original = ET.fromstring(svg)
    if original.find(".//" + NS + "style") is not None or original.get("style"):
        svg = tangent_native.presentation(svg)
    root = ET.fromstring(graph_tangents.render_svg(entry, svg))
    vertices, right, vertical, horizontal, _ = graph_tangents.model(entry)
    ox, oy = entry["svg_origin"]
    _ux, uy = entry["svg_unit"]
    triangle = list(root)[-1]
    labels = {n.text: n for n in triangle if n.tag == NS + "text"}
    if vertices[vertical][1] < vertices[right][1]:
        # For falling tangents the vertical endpoint lies below the right angle;
        # put its letter below it, rather than on top of the other vertex letter.
        labels[vertical].set("y", str(oy - float(vertices[vertical][1]) * uy + 16))
        labels[right].set("y", str(oy - float(vertices[right][1]) * uy - 6))
    if vertices[horizontal][1] == 0:
        labels[horizontal].set("y", str(oy - 7))
    if vertices[right] == (0, 0):
        labels[right].set("x", str(ox + 12))
        labels[right].set("y", str(oy + 28))
    left, top, width, height = map(float, root.get("viewBox").replace(",", " ").split())
    for label in labels.values():
        label.set(
            "x", str(min(left + width - 14, max(left + 4, float(label.get("x")))))
        )
        label.set("y", str(min(top + height - 4, max(top + 16, float(label.get("y"))))))
    # Source authoring exports may contain harmless inline paint declarations;
    # generated assets must use upload-compatible presentation attributes.
    for n in root.iter():
        style = n.attrib.pop("style", "")
        for declaration in style.split(";"):
            if not declaration.strip():
                continue
            name, value = declaration.split(":", 1)
            if name.strip() not in (
                "stop-color",
                "stop-opacity",
                "fill",
                "stroke",
                "opacity",
            ):
                raise UnsupportedCondition("unrecognized native SVG paint style")
            n.set(name.strip(), value.strip())
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context, *, condition_asset_bytes=None):
    _, asset = _read(context)
    svg, entry, converted = recover(condition_asset_bytes)
    return (
        *((solution_diagrams.spec(asset["asset_key"], svg),) if converted else ()),
        solution_diagrams.spec(KEY, _solution(svg, entry)),
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    condition, asset = _read(context)
    content = context["normalized_content"]
    svg, entry, converted = recover(condition_asset_bytes)
    result, html = graph_tangents.proof(entry)
    html = re.sub(r"-\(([0-9]+(?:,[0-9]+)?)\)", r"-\1", html)
    figure, key, changes = solution_diagrams.image(
        content,
        KEY,
        ALT,
        svg=_solution(svg, entry),
        generated=generated_solution_assets,
    )
    solution = next((s for s in content["sections"] if s["key"] == "solution"), None)
    removed = tuple(
        {"transformation_target_id": "asset:" + a["asset_key"], "operation": "remove"}
        for a in content["assets"]
        if a["asset_key"] in (solution or {}).get("asset_keys", [])
        and a["asset_key"] not in (key, asset["asset_key"])
    )
    plan = solution_diagrams.repair(
        condition,
        _targeted(next((s for s in content["sections"] if s["key"] == "answer"), None)),
        _targeted(solution),
        result,
        figure + html,
        (key,),
        removed + tuple(changes),
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    extra = []
    if converted:
        digest = hashlib.sha256(svg.encode()).hexdigest()
        prepared = [
            a
            for a in generated_solution_assets
            if a["asset_key"] == asset["asset_key"] and a["sha256"] == digest
        ]
        if len(prepared) != 1:
            raise UnsupportedCondition("the prepared SVG must match this source PNG")
        new = prepared[0]
        image["data-asset-id"] = new["source_asset_id"]
        image["src"] = new["url"]
        image["alt"] = "График функции и касательная"
        image["data-transformation-target-id"] = "asset:" + asset["asset_key"]
        extra.append(
            {
                "transformation_target_id": "asset:" + asset["asset_key"],
                "operation": "rewrite",
                "value": {
                    "asset_key": asset["asset_key"],
                    "asset_id": new["source_asset_id"],
                    "url": new["url"],
                    "kind": "ordinary_image",
                    "alt": image["alt"],
                    "parent_target_id": _targeted(condition)[
                        "transformation_target_id"
                    ],
                    "position": 0,
                    "html": str(image),
                },
            }
        )

    def inline(x):
        return '<span data-inline-latex="' + escape(x, quote=True) + '"></span>'

    def canonical(x):
        s = BeautifulSoup(x or "", "html.parser")
        for tag in s.find_all(True):
            tag.attrs.pop("data-transformation-target-id", None)
        return str(s)

    condition_html = canonical(
        "<p>На рисунке изображены график функции "
        + inline("y=f(x)")
        + " и касательная к нему в точке с абсциссой "
        + inline("x_0")
        + ".</p><p>Найдите значение производной функции "
        + inline("f(x)")
        + " в точке "
        + inline("x_0")
        + ".</p><center>"
        + str(image)
        + "</center>"
    )
    if canonical(condition["html"]) != condition_html:
        change = rewrite(
            _targeted(condition),
            "condition",
            condition.get("title", "Условие"),
            condition_html,
        )
        change["value"]["asset_keys"] = list(condition["asset_keys"])
        extra.append(change)
    expected = canonical(plan.solution_html)
    out = []
    for t in plan.transformations:
        t = deepcopy(t)
        if t["transformation_target_id"].startswith("section:solution"):
            if solution is not None and canonical(solution["html"]) == expected:
                continue
            t["value"]["html"] = expected
        out.append(t)
    return replace(plan, solution_html=expected, transformations=tuple(extra + out))
