"""Scoped derivative-level diagrams using the existing constrained graph fitter."""

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from html import escape
from pathlib import Path

import sympy as sp
from bs4 import BeautifulSoup

from ..equations.linear_system_intervals import interval_latex
from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition, rewrite
from ..triangles.right.basic_parent import _targeted
from . import (
    derivative_level_geometry,
    derivative_level_input,
    derivative_level_render,
    graph_stationary,
)

derivative_level_curves = derivative_level_input.derivative_level_curves
raster_primitive = derivative_level_input.raster_primitive
primitive_curves = derivative_level_input.primitive_curves
_read = derivative_level_input._read
_recover = derivative_level_input._recover
_input = derivative_level_input._input
_render = derivative_level_render._render
_solution_svg = derivative_level_render._solution_svg
proof = derivative_level_render.proof


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


_native_entry = derivative_level_geometry._native_entry


_model_entry = derivative_level_geometry._model_entry


_intersections = derivative_level_geometry._intersections


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


def _reviewed_horizontal_plan(
    context, condition_asset_bytes, generated_solution_assets
):
    from . import stationary_raster_runner

    q, condition, _, entry, points = _reviewed_horizontal(
        context, condition_asset_bytes
    )
    content = context["normalized_content"]
    svg = graph_stationary.render_svg(entry, condition_asset_bytes, q.interval, points)
    figure, key, changes = solution_diagrams.image(
        content,
        KEY,
        "Точки с горизонтальной касательной",
        svg=svg,
        generated=generated_solution_assets,
    )
    return solution_diagrams.repair(
        condition,
        _targeted(next((s for s in content["sections"] if s["key"] == "answer"), None)),
        _targeted(
            next((s for s in content["sections"] if s["key"] == "solution"), None)
        ),
        str(len(points)),
        figure + stationary_raster_runner.proof(q, points),
        (key,),
        changes,
    )


def _replace_condition_raster(
    plan, condition, asset, source, generated_solution_assets
):
    data, model = source
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
            return _reviewed_horizontal_plan(
                context, condition_asset_bytes, generated_solution_assets
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
    return _replace_condition_raster(
        plan, condition, asset, (data, model), generated_solution_assets
    )


def _rewrite_derivative_condition(context, changes, canonical):
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
        return '<span data-inline-latex="' + escape(formula, quote=True) + '"></span>'

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
    return changes


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
        changes = _rewrite_derivative_condition(context, changes, canonical)
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
