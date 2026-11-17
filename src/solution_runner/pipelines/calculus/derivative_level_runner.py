"""Scoped derivative-level diagrams using the existing constrained graph fitter."""

import hashlib
import io
import json
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from functools import lru_cache
from html import escape
from itertools import pairwise
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import sympy as sp
from bs4 import BeautifulSoup
from PIL import Image

from ..equations.linear_system_intervals import Interval, interval_latex
from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition, normalize, rewrite
from ..triangles.right.basic_parent import _targeted
from . import (
    curve_levels,
    derivative_level_curves,
    graph_derivative_levels,
    graph_input,
    graph_stationary,
    primitive_curves,
    primitive_svg,
    raster_primitive,
)


def _horizontal(context):
    from . import stationary_raster_runner

    try:
        stationary_raster_runner._read(context)
    except UnsupportedCondition:
        return False
    return True


KEY = "derivative_level_points"
ALT = "Горизонтальная прямая и точки её пересечения с графиком производной"
CACHE = Path(__file__).with_name("assets") / "derivative-level-curves.json"
NS = "{http://www.w3.org/2000/svg}"


def _read(context):
    clean = deepcopy(context)
    content = clean["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    if len(condition.get("asset_keys", [])) != 1:
        raise UnsupportedCondition("one derivative graph is required")
    asset = next(
        a for a in content["assets"] if a["asset_key"] == condition["asset_keys"][0]
    )
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) != 1 or images[0].get("data-asset-id") != asset["asset_id"]:
        raise UnsupportedCondition("the visible derivative graph must match its asset")
    images[0].decompose()
    condition["html"] = str(soup)
    condition["asset_keys"] = []
    content["assets"] = []
    text = normalize(graph_input._read_text(clean)[4])
    text = text.replace(
        "график производной функции y=f'(x)— производной функции f(x)",
        "график производной функции f(x)",
    )
    text = text.replace(
        "график функции y=f'(x)— производной функции f(x)",
        "график производной функции f(x)",
    )
    text = text.replace(
        "график производной функции f'(x)", "график производной функции f(x)"
    )
    question = graph_derivative_levels.parse(text)
    if not question.count or question.domain is None:
        raise UnsupportedCondition(
            "an explicit interval and a derivative-level count are required"
        )
    domain = Interval(*map(Fraction, question.domain))
    trace_question = graph_stationary.Question(
        "count", domain, domain, horizontal=Fraction(question.slope)
    )
    return (
        question,
        trace_question,
        next(
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        ),
        asset,
    )


def _reviewed_horizontal(context, data):
    from . import stationary_raster_runner

    question, condition, asset = stationary_raster_runner._read(context)
    entries = json.loads(
        (
            Path(__file__).with_name("assets")
            / "derivative-level-native-horizontal.json"
        ).read_text()
    )
    entry = entries.get(hashlib.sha256(data).hexdigest())
    if entry is None or entry["domain"] != [
        str(question.domain.lower),
        str(question.domain.upper),
    ]:
        raise UnsupportedCondition(
            "the native horizontal graph requires reviewed evidence"
        )
    return (
        question,
        condition,
        asset,
        entry["frame"],
        graph_stationary.select(entry["points"], question.interval),
    )


def required_assets(context):
    if _horizontal(context):
        from . import stationary_raster_runner

        return stationary_raster_runner.required_assets(context)
    _read(context)
    return ()


def _render(model):
    return raster_primitive.render(model).replace("y = F(x)", "y = f′(x)")


@lru_cache(maxsize=160)
def _recover(data, question):
    digest = hashlib.sha256(data).hexdigest()
    if CACHE.exists():
        cached = json.loads(CACHE.read_text()).get(digest)
        if cached is not None:
            if cached["source_sha256"] != digest or cached["domain"] != [
                str(question.domain.lower),
                str(question.domain.upper),
            ]:
                raise UnsupportedCondition("the cached graph domain changed")
            primitive_curves.verify(cached)
            return cached
    png = data
    if data.startswith(b"\xff\xd8"):
        output = io.BytesIO()
        Image.open(io.BytesIO(data)).save(output, format="PNG")
        png = output.getvalue()
    model = derivative_level_curves.recover(png, question)
    model["source_sha256"] = digest
    return model


def _native_entry(data, question):
    frame, extrema = primitive_svg.read(data, question)
    root = ET.fromstring(data)
    axes = []
    for n in root.iter(NS + "line"):
        if n.get("stroke", "").lower() not in ("black", "#000000", "#000"):
            continue
        x1, y1, x2, y2 = (float(n.get(k, "0")) for k in ("x1", "y1", "x2", "y2"))
        if abs(y2 - y1) < 0.001 and abs(x2 - x1) > frame["svg_unit"] * 3:
            axes.append((abs(x2 - x1), y1))
    if not axes:
        raise UnsupportedCondition(
            "the native derivative graph needs a horizontal coordinate axis"
        )
    oy = max(axes)[1]
    segments = []
    for n in root.iter(NS + "path"):
        if n.get("stroke", "").lower() == "#143b8f":
            segments.extend(primitive_svg._segments(n.get("d", "")))
    segments = [
        s if s[-1, 0] > s[0, 0] else s[::-1]
        for s in segments
        if abs(s[-1, 0] - s[0, 0]) > 1e-6
    ]
    segments.sort(key=lambda s: s[0, 0])
    unit = frame["svg_unit"]
    for before, after in pairwise(segments):
        p = before[-1]
        incoming = p[1] - before[-2, 1]
        outgoing = after[1, 1] - after[0, 1]
        if incoming * outgoing < 0 and not any(
            abs(v["svg"][0] - p[0]) < unit * 0.05 for v in extrema
        ):
            extrema.append({"svg": p.tolist()})
    extrema.sort(key=lambda v: v["svg"][0])
    nodes = []
    for p, endpoint in [
        (segments[0][0], True),
        *[(n["svg"], False) for n in extrema],
        (segments[-1][-1], True),
    ]:
        y = (oy - float(p[1])) / unit
        node = {"svg": list(p), "endpoint": endpoint}
        if abs(y - round(y)) < 0.035:
            node["y"] = str(round(y))
        else:
            node["y_bounds"] = [str(y - 0.02), str(y + 0.02)]
        nodes.append(node)
    return {
        "svg_origin": [frame["svg_origin"][0], oy],
        "svg_unit": unit,
        "curve_segments": [s.tolist() for s in segments],
        "curve_nodes": nodes,
    }


def _model_entry(model):
    segments = np.asarray(model["bezier_segments"])
    nodes = []
    anchors = [
        (segments[0, 0], True),
        *[((p["x"], p["y"]), False) for p in model["extrema"]],
        (segments[-1, -1], True),
    ]
    for p, endpoint in anchors:
        y = float(p[1])
        node = {"svg": [float(p[0]) * 20, -y * 20], "endpoint": endpoint}
        if abs(y - round(y)) < 0.06:
            node["y"] = str(round(y))
        else:
            node["y_bounds"] = [str(y - 0.06), str(y + 0.06)]
        nodes.append(node)
    transformed = segments.copy() * 20
    transformed[:, :, 1] *= -1
    return {
        "svg_origin": [0, 0],
        "svg_unit": 20,
        "curve_segments": transformed.tolist(),
        "curve_nodes": nodes,
    }


def _intersections(entry, level):
    points = curve_levels.svg_intersections(entry, level)
    nodes = entry["curve_nodes"]
    for i, node in enumerate(nodes):
        if curve_levels.ordinate_sign(node, level) != 0:
            continue
        left = nodes[max(0, i - 1)]["svg"][0]
        right = nodes[min(len(nodes) - 1, i + 1)]["svg"][0]
        points = [p for p in points if not left - 1e-6 <= p[0] <= right + 1e-6]
        if not node.get("endpoint", False):
            points.append(
                (
                    node["svg"][0],
                    entry["svg_origin"][1] - float(level) * entry["svg_unit"],
                )
            )
    unique = curve_levels.distinct_points(
        points, nodes[0]["svg"][0], nodes[-1]["svg"][0]
    )
    if len(unique) != curve_levels.count(nodes, level):
        raise UnsupportedCondition(
            "the SVG intersections and monotone-arc count disagree"
        )
    return unique


def _input(context, data):
    q, trace_q, condition, asset = _read(context)
    model = None
    if data.startswith((raster_primitive.PNG, b"\xff\xd8")):
        model = deepcopy(_recover(data, trace_q))
    elif raster_primitive.META.encode() in data:
        canonical = data.replace("y = f′(x)".encode(), b"y = F(x)")
        model = raster_primitive.embedded(canonical, trace_q)
        cached = (
            json.loads(CACHE.read_text()).get(model["source_sha256"])
            if CACHE.exists()
            else None
        )
        if cached is not None:
            if cached["domain"] != model["domain"] or cached["span"] != model["span"]:
                raise UnsupportedCondition(
                    "the revised source graph has different intervals"
                )
            primitive_curves.verify(cached)
            model = deepcopy(cached)
    if model is not None:
        entry = _model_entry(model)
        points = _intersections(entry, q.slope)
    elif asset["asset_id"] in graph_input.EVIDENCE:
        parsed, q, entry, points, result = graph_derivative_levels._input(context)
        from ..probability import condition_diagram

        condition_diagram.verify_download(parsed[6], data)
        return q, condition, asset, entry, points, None, result
    else:
        entry = _native_entry(data, trace_q)
        points = _intersections(entry, q.slope)
    answer = next(
        (s for s in context["normalized_content"]["sections"] if s["key"] == "answer"),
        {},
    )
    stored = BeautifulSoup(answer.get("html", ""), "html.parser").get_text(strip=True)
    reviewed_path = (
        Path(__file__).with_name("assets") / "derivative-level-reviewed-counts.json"
    )
    reviews = json.loads(reviewed_path.read_text()) if reviewed_path.exists() else {}
    approved = reviews.get(
        model["source_sha256"]
        if model is not None
        else hashlib.sha256(data).hexdigest()
    )
    reviewed = (
        approved is not None
        and approved["domain"] == [str(x) for x in q.domain]
        and approved["slope"] == str(q.slope)
        and approved["count"] == len(points)
    )
    if (
        not reviewed
        and stored.isdigit()
        and str(int(stored)) == stored
        and int(stored) != len(points)
    ):
        raise UnsupportedCondition(
            f"the recovered level count {len(points)} differs from the stored answer {stored}; visual review is required"
        )
    return q, condition, asset, entry, points, model, str(len(points))


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


def diagram_specs(context, *, condition_asset_bytes=None):
    if _horizontal(context):
        from . import stationary_raster_runner

        try:
            return stationary_raster_runner.diagram_specs(
                context, condition_asset_bytes=condition_asset_bytes
            )
        except UnsupportedCondition:
            q, _, _, entry, points = _reviewed_horizontal(
                context, condition_asset_bytes
            )
            return (
                solution_diagrams.spec(
                    KEY,
                    graph_stationary.render_svg(
                        entry, condition_asset_bytes, q.interval, points
                    ),
                ),
            )
    if condition_asset_bytes is None:
        return ()
    q, _, asset, entry, points, model, _ = _input(context, condition_asset_bytes)
    specs = []
    if model is not None and _render(model).encode() != condition_asset_bytes:
        specs.append(solution_diagrams.spec(asset["asset_key"], _render(model)))
    specs.append(
        solution_diagrams.spec(
            KEY, _solution_svg(condition_asset_bytes, q, entry, points, model)
        )
    )
    return tuple(specs)


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


def _build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    if _horizontal(context):
        from . import stationary_raster_runner

        try:
            return stationary_raster_runner.build_context_repair_plan(
                context,
                condition_asset_bytes=condition_asset_bytes,
                generated_solution_assets=generated_solution_assets,
            )
        except UnsupportedCondition:
            q, condition, _, entry, points = _reviewed_horizontal(
                context, condition_asset_bytes
            )
            content = context["normalized_content"]
            svg = graph_stationary.render_svg(
                entry, condition_asset_bytes, q.interval, points
            )
            figure, key, changes = solution_diagrams.image(
                content,
                KEY,
                "Точки с горизонтальной касательной",
                svg=svg,
                generated=generated_solution_assets,
            )
            return solution_diagrams.repair(
                condition,
                _targeted(
                    next((s for s in content["sections"] if s["key"] == "answer"), None)
                ),
                _targeted(
                    next(
                        (s for s in content["sections"] if s["key"] == "solution"), None
                    )
                ),
                str(len(points)),
                figure + stationary_raster_runner.proof(q, points),
                (key,),
                changes,
            )
    data = condition_asset_bytes
    if not isinstance(data, bytes):
        raise UnsupportedCondition("current derivative graph bytes are required")
    q, condition, asset, entry, points, model, result = _input(context, data)
    content = context["normalized_content"]
    svg = _solution_svg(data, q, entry, points, model)
    figure, key, changes = solution_diagrams.image(
        content, KEY, ALT, svg=svg, generated=generated_solution_assets
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
        figure + proof(q, result),
        (key,),
        removed + tuple(changes),
    )
    if model is None or _render(model).encode() == data:
        return plan
    digest = hashlib.sha256(_render(model).encode()).hexdigest()
    candidates = [
        a
        for a in generated_solution_assets
        if a.get("asset_key") == asset["asset_key"] and a.get("sha256") == digest
    ]
    if len(candidates) != 1:
        raise UnsupportedCondition("the converted SVG must match the current raster")
    new = candidates[0]
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    image["data-asset-id"] = new["source_asset_id"]
    image["src"] = new["url"]
    image["alt"] = "График производной функции"
    image["data-transformation-target-id"] = "asset:" + asset["asset_key"]
    asset_change = {
        "transformation_target_id": "asset:" + asset["asset_key"],
        "operation": "rewrite",
        "value": {
            "asset_key": asset["asset_key"],
            "asset_id": new["source_asset_id"],
            "url": new["url"],
            "kind": "ordinary_image",
            "alt": image["alt"],
            "parent_target_id": _targeted(condition)["transformation_target_id"],
            "position": 0,
            "html": str(image),
        },
    }
    condition_change = rewrite(
        _targeted(condition), "condition", condition.get("title", "Условие"), str(soup)
    )
    condition_change["value"]["asset_keys"] = list(condition["asset_keys"])
    return replace(
        plan, transformations=(asset_change, condition_change, *plan.transformations)
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    """Compare materialized DOMs so a second run does not rewrite identical work."""
    plan = _build_context_repair_plan(
        context,
        condition_asset_bytes=condition_asset_bytes,
        generated_solution_assets=generated_solution_assets,
    )
    content = context["normalized_content"]

    def canonical(html):
        soup = BeautifulSoup(html or "", "html.parser")
        for tag in soup.find_all(True):
            tag.attrs.pop("data-transformation-target-id", None)
            if tag.name == "img":
                asset = next(
                    (
                        a
                        for a in content.get("assets", [])
                        if a["asset_key"] == tag.get("data-asset-key")
                        and a["asset_id"] == tag.get("data-asset-id")
                    ),
                    None,
                )
                if asset is not None:
                    tag["alt"] = asset.get("alt", "")
        return str(soup)

    current = next((s for s in content["sections"] if s["key"] == "solution"), None)
    expected = canonical(plan.solution_html)
    changes = []
    for original in plan.transformations:
        change = deepcopy(original)
        if change["transformation_target_id"].startswith("section:solution"):
            if current is not None and canonical(current["html"]) == expected:
                continue
            change["value"]["html"] = expected
        changes.append(change)
    if not _horizontal(context):
        q, tq, condition, _asset = _read(context)
        previous = next(
            (
                t["value"]["html"]
                for t in reversed(changes)
                if t["transformation_target_id"].startswith("section:condition")
            ),
            condition["html"],
        )
        image = BeautifulSoup(previous, "html.parser").find("img")

        def inline(formula):
            return (
                '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'
            )

        condition_html = canonical(
            "<p>На рисунке изображён график производной функции "
            + inline("f(x)")
            + ", определённой на интервале "
            + inline(interval_latex(tq.domain))
            + ".</p>"
            + "<p>Найдите количество точек, в которых касательная к графику функции "
            + inline("f(x)")
            + " параллельна прямой "
            + inline("y=" + sp.latex(q.comparison))
            + " или совпадает с ней.</p><center>"
            + str(image)
            + "</center>"
        )
        changes = [
            t
            for t in changes
            if not t["transformation_target_id"].startswith("section:condition")
        ]
        if canonical(condition["html"]) != condition_html:
            change = rewrite(
                _targeted(condition),
                "condition",
                condition.get("title", "Условие"),
                condition_html,
            )
            change["value"]["asset_keys"] = list(condition["asset_keys"])
            changes.append(change)
    if _horizontal(context):
        from . import stationary_raster_runner

        q, condition, _asset = stationary_raster_runner._read(context)
        previous = next(
            (
                t["value"]["html"]
                for t in reversed(changes)
                if t["transformation_target_id"].startswith("section:condition")
            ),
            condition["html"],
        )
        image = BeautifulSoup(previous, "html.parser").find("img")

        def inline(formula):
            return (
                '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'
            )

        condition_html = canonical(
            "<p>На рисунке изображён график функции "
            + inline("y=f(x)")
            + ", определённой на интервале "
            + inline(interval_latex(q.domain))
            + ".</p><p>Найдите количество точек, в которых касательная к графику функции параллельна прямой "
            + inline("y=" + str(q.horizontal))
            + (" или совпадает с ней" if q.include_coincident else "")
            + ".</p><center>"
            + str(image)
            + "</center>"
        )
        changes = [
            t
            for t in changes
            if not t["transformation_target_id"].startswith("section:condition")
        ]
        if canonical(condition["html"]) != condition_html:
            change = rewrite(
                _targeted(condition),
                "condition",
                condition.get("title", "Условие"),
                condition_html,
            )
            change["value"]["asset_keys"] = list(condition["asset_keys"])
            changes.append(change)
    return replace(plan, solution_html=expected, transformations=tuple(changes))
