"""Audited two-point tangents, constructed in the solution with a right triangle."""

import re
from copy import deepcopy
from dataclasses import replace
from itertools import pairwise
from statistics import median
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from ..probability import condition_diagram, solution_diagrams
from ..probability.common import UnsupportedCondition
from . import graph_composites, graph_input, graph_tangents, tangent_native
from .tangent_slope_runner import _solution

KEY = graph_input.KEY
NS = "{http://www.w3.org/2000/svg}"


def _input(context):
    data = graph_input.read_graph(context)
    text, evidence, source = data[4:]
    entry = deepcopy(evidence)
    origin = graph_composites._ORIGIN.fullmatch(text)
    if origin:
        _, question = graph_composites._input(context)
        x, y = question.point["x"], question.point["y"]
        entry["vertices"] = {"A": [str(x), str(y)], "B": [str(x), "0"], "C": ["0", "0"]}
    elif not graph_tangents._QUESTION.fullmatch(text):
        raise UnsupportedCondition(
            "the complete two-point tangent question is required"
        )
    graph_tangents.model(entry)
    # Only the solution is reconstructed. The original condition SVG is immutable.
    root = ET.fromstring(
        tangent_native.presentation(
            source.encode() if isinstance(source, str) else source
        )
    )
    segments = tangent_native.straight_segments(root)
    black = [
        p
        for n, p in segments
        if n.get("stroke", "").lower() in ("black", "#000", "#000000", "#010202")
    ]
    horizontal = [p for p in black if abs(p[3] - p[1]) < 0.5 and abs(p[2] - p[0]) > 30]
    vertical = [p for p in black if abs(p[2] - p[0]) < 0.5 and abs(p[3] - p[1]) > 30]
    if not horizontal or not vertical:
        raise UnsupportedCondition("the source coordinate axes are required")
    ox = max(vertical, key=lambda p: abs(p[3] - p[1]))[0]
    oy = max(horizontal, key=lambda p: abs(p[2] - p[0]))[1]
    gray = [p for n, p in segments if n.get("stroke", "").lower() == "#adaaaa"]
    xs = sorted({p[0] for p in gray if abs(p[2] - p[0]) < 0.5})
    ys = sorted({p[1] for p in gray if abs(p[3] - p[1]) < 0.5})
    if len(xs) < 4 or len(ys) < 4:
        raise UnsupportedCondition(
            "the audited diagram needs a visible coordinate grid"
        )
    ux = median(b - a for a, b in pairwise(xs) if b - a > 1)
    uy = median(b - a for a, b in pairwise(ys) if b - a > 1)
    for key, value in {
        "svg_origin": [ox, oy],
        "svg_unit": [ux, uy],
        "svg_bounds": [min(xs), min(ys), max(xs), max(ys)],
        "svg_label": [ox + ux * 2, oy - uy * 0.7],
    }.items():
        entry.setdefault(key, value)
    return data, entry, bool(origin)


def required_assets(context):
    _input(context)
    return ()


def _diagram(entry, source, origin):
    if origin:
        source = graph_composites.render_origin_tangent(entry, source)
    root = ET.fromstring(_solution(source, entry))
    if origin:
        # Keep B clear of the original numeric abscissa label.
        label = next(
            n for n in list(root)[-1] if n.tag == NS + "text" and n.text == "B"
        )
        label.set("x", str(float(label.get("x")) + 10))
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context, *, condition_asset_bytes=None):
    data, entry, origin = _input(context)
    if condition_asset_bytes is not None:
        condition_diagram.verify_download(data[-1], condition_asset_bytes)
    return (solution_diagrams.spec(KEY, _diagram(entry, data[-1], origin)),)


def _canonical(html):
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup.find_all(True):
        tag.attrs.pop("data-transformation-target-id", None)
    return str(soup)


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data, entry, origin = _input(context)
    content, condition, ans, solution, _, _, source = data
    condition_diagram.verify_download(source, condition_asset_bytes)
    result, html = graph_tangents.proof(entry)
    html = re.sub(r"-\(([0-9]+(?:,[0-9]+)?)\)", r"-\1", html)
    if origin:
        x, y = entry["vertices"]["A"]
        html = (
            f"<p>Проведём касательную через начало координат и отмеченную точку ({x}; {y}).</p>"
            + html.replace("x_0", x)
        )
    figure, key, changes = solution_diagrams.image(
        content,
        KEY,
        graph_input.ALT,
        svg=_diagram(entry, source, origin),
        generated=generated_solution_assets,
    )
    removed = tuple(
        {"transformation_target_id": "asset:" + a["asset_key"], "operation": "remove"}
        for a in content["assets"]
        if a["asset_key"] in (solution or {}).get("asset_keys", [])
        and a["asset_key"] not in (key, *condition["asset_keys"])
    )
    plan = solution_diagrams.repair(
        condition,
        ans,
        solution,
        result,
        _canonical(figure + html),
        (key,),
        removed + tuple(changes),
    )
    transformations = tuple(
        t
        for t in plan.transformations
        if not (
            t["transformation_target_id"].startswith("section:solution")
            and solution
            and _canonical(solution["html"]) == plan.solution_html
            and solution.get("asset_keys", []) == [key]
        )
    )
    return replace(plan, transformations=transformations)
