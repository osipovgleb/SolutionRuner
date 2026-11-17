"""Derivative-level abscissas and counts using the established graph workflow."""

import hashlib
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import sympy as sp
from bs4 import BeautifulSoup

from ..equations.linear_system_intervals import interval_latex
from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition, rewrite
from ..triangles.right.basic_parent import _targeted
from . import (
    derivative_abscissa_input,
    derivative_abscissa_render,
    derivative_level_geometry,
    derivative_level_input,
    derivative_level_render,
)

derivative_level_curves = derivative_level_input.derivative_level_curves
raster_primitive = derivative_level_input.raster_primitive
primitive_curves = derivative_level_input.primitive_curves
_read = derivative_abscissa_input.read
_recover = derivative_level_input._recover
_input = derivative_abscissa_input.input
_render = derivative_level_render._render
_solution_svg = derivative_abscissa_render.solution_svg
proof = derivative_abscissa_render.proof


KEY = "derivative_level_points"
ALT = "Горизонтальная прямая и точки её пересечения с графиком производной"
CACHE = Path(__file__).with_name("assets") / "derivative-level-curves.json"
NS = "{http://www.w3.org/2000/svg}"


def required_assets(context):
    derivative_abscissa_input.read(context)
    return ()


_native_entry = derivative_level_geometry._native_entry


_model_entry = derivative_level_geometry._model_entry


_intersections = derivative_level_geometry._intersections


def diagram_specs(context, *, condition_asset_bytes=None):
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


def _build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
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


def _rewrite_condition(context, changes, canonical):
    q, condition, _asset = derivative_abscissa_input.read(context)
    previous = next(
        (
            t["value"]["html"]
            for t in reversed(changes)
            if t["transformation_target_id"].startswith("section:condition")
        ),
        condition["html"],
    )
    image = BeautifulSoup(previous, "html.parser").find("img")
    inline = derivative_abscissa_render.inline
    domain = ""
    if q.domain is not None:
        from fractions import Fraction

        from ..equations.linear_system_intervals import Interval

        domain = ", определённой на интервале " + inline(
            interval_latex(Interval(*map(Fraction, q.domain)))
        )
    request = (
        "количество точек, в которых"
        if q.count
        else (
            "наименьшую абсциссу точки, в которой"
            if q.smallest
            else "абсциссу точки, в которой"
        )
    )
    comparison = (
        "оси абсцисс"
        if q.comparison is None
        else "прямой " + inline("y=" + sp.latex(q.comparison))
    )
    condition_html = canonical(
        "<p>На рисунке изображён график производной функции "
        + inline("f(x)")
        + domain
        + ".</p>"
        + "<p>Найдите "
        + request
        + " касательная к графику функции "
        + inline("f(x)")
        + " параллельна "
        + comparison
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
    changes = _rewrite_condition(context, changes, canonical)
    return replace(plan, solution_html=expected, transformations=tuple(changes))
