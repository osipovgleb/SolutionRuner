"""Trapezoid PNG-to-SVG conversion in ordinary group prepare/apply."""

import hashlib
from copy import deepcopy
from dataclasses import dataclass, replace

import sympy as sp
from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition, line, rewrite
from ..triangles.right.basic_parent import _targeted
from . import graph_input, graph_integrals, raster_rays
from .common import X, answer
from .graph_integral_proof import difference_name, number

KEY = "integral_shading"
ALT = "Площадь под графиком функции на заданном отрезке"


def _read(context):
    content = context["normalized_content"]
    conditions = [s for s in content["sections"] if s["key"] == "condition"]
    if len(conditions) != 1 or len(conditions[0].get("asset_keys", [])) != 1:
        raise UnsupportedCondition("one complete two-ray condition image is required")
    condition = conditions[0]
    key = condition["asset_keys"][0]
    assets = [a for a in content["assets"] if a.get("asset_key") == key]
    if len(assets) != 1 or assets[0].get("kind") != "ordinary_image":
        raise UnsupportedCondition("the condition ray image is ambiguous")
    asset = assets[0]
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-id") != asset["asset_id"]
        or images[0].get("data-asset-key") != key
    ):
        raise UnsupportedCondition("the visible ray graph does not match its asset")
    clean = deepcopy(context)
    image_soup = BeautifulSoup(condition["html"], "html.parser")
    image_soup.find("img").decompose()
    cond = next(
        s for s in clean["normalized_content"]["sections"] if s["key"] == "condition"
    )
    cond["html"] = str(image_soup)
    cond["asset_keys"] = []
    clean["normalized_content"]["assets"] = []
    q = graph_integrals.parse(graph_input._read_text(clean)[4])
    if q.operation != "difference":
        raise UnsupportedCondition(
            "the raster rays need the complete primitive difference question"
        )
    return q, condition, asset


def required_assets(context):
    condition = next(
        s for s in context["normalized_content"]["sections"] if s["key"] == "condition"
    )
    assets = [
        a
        for a in context["normalized_content"]["assets"]
        if a["asset_key"] in condition.get("asset_keys", [])
    ]
    if len(assets) == 1 and assets[0]["asset_id"] in graph_input.EVIDENCE:
        return graph_integrals.required_assets(context)
    return ()


def _model(context, data):
    q, condition, asset = _read(context)
    if data.startswith(raster_rays.PNG):
        if any(
            a["asset_key"] not in (asset["asset_key"], KEY)
            for a in context["normalized_content"]["assets"]
        ):
            raise UnsupportedCondition("unrelated graph assets need separate review")
        model = raster_rays.recover(data, q.lower, q.upper)
    else:
        model = raster_rays.embedded(data, q.lower, q.upper)
    return q, condition, asset, model


def diagram_specs(context, *, condition_asset_bytes=None):
    if not isinstance(condition_asset_bytes, bytes):
        return ()
    q, condition, asset, model = _model(context, condition_asset_bytes)
    if model is None:
        return ()
    condition_specs = (
        (solution_diagrams.spec(asset["asset_key"], raster_rays.render(model)),)
        if condition_asset_bytes.startswith(raster_rays.PNG)
        else ()
    )
    return (
        *condition_specs,
        solution_diagrams.spec(KEY, raster_rays.render(model, shaded=True)),
    )


@dataclass(frozen=True)
class Area:
    lower: sp.Rational
    upper: sp.Rational
    height: sp.Rational
    join: sp.Rational
    zero: sp.Rational
    rising: bool
    result: sp.Rational


def calculate(question, model):
    a, b = question.lower, question.upper
    h, c, z = map(sp.Rational, (model["height"], model["join"], model["zero"]))
    rising = model["rising"]
    if h <= 0 or not a < c < b or rising != (c > z) or (z != a if rising else z != b):
        raise UnsupportedCondition(
            "the two rays do not bound the requested positive trapezoid"
        )
    slope = h / (c - z)
    diagonal = sp.expand(slope * (X - z))
    integral = (
        sp.integrate(diagonal, (X, a, c)) + h * (b - c)
        if rising
        else h * (c - a) + sp.integrate(diagonal, (X, c, b))
    )
    small = b - c if rising else c - a
    geometric = h * (b - a + small) / 2
    if integral != geometric:
        raise UnsupportedCondition("the geometric and analytic ray areas disagree")
    return Area(a, b, h, c, z, rising, sp.simplify(integral))


def proof(m):
    small = m.upper - m.join if m.rising else m.join - m.lower
    small_expression = (
        number(m.upper) + "-" + number(m.join)
        if m.rising
        else number(m.join) + "-" + number(m.lower)
    )
    html = "<p>Разность значений первообразной равна площади выделенной на рисунке трапеции:</p>"
    html += line(
        difference_name(m)
        + r"=\int_{"
        + number(m.lower)
        + "}^{"
        + number(m.upper)
        + r"}f(x)\,dx=S"
    )
    html += "<p>Длины параллельных оснований и высота трапеции:</p>"
    html += line("B_1=" + small_expression + "=" + number(small))
    html += line(
        "B_2="
        + number(m.upper)
        + "-"
        + number(m.lower)
        + "="
        + number(m.upper - m.lower)
    )
    html += line("h=" + number(m.height))
    html += line(
        difference_name(m)
        + r"=\frac{"
        + number(small)
        + "+"
        + number(m.upper - m.lower)
        + r"}{2}\cdot"
        + number(m.height)
        + "="
        + number(m.result)
    )
    return html


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data = condition_asset_bytes
    if not isinstance(data, bytes):
        raise UnsupportedCondition("the current ray diagram bytes are required")
    q, condition, asset, model = _model(context, data)
    if model is None:
        return graph_integrals.build_context_repair_plan(
            context, condition_asset_bytes=data
        )
    m = calculate(q, model)
    content = context["normalized_content"]
    shade = raster_rays.render(model, shaded=True)
    figure, key, changes = solution_diagrams.image(
        content, KEY, ALT, svg=shade, generated=generated_solution_assets
    )
    result = solution_diagrams.repair(
        condition,
        _targeted(next((s for s in content["sections"] if s["key"] == "answer"), None)),
        _targeted(
            next((s for s in content["sections"] if s["key"] == "solution"), None)
        ),
        answer(m.result),
        figure + proof(m),
        (key,),
        changes,
    )
    if not data.startswith(raster_rays.PNG):
        return result
    svg = raster_rays.render(model)
    digest = hashlib.sha256(svg.encode()).hexdigest()
    generated = [
        a
        for a in generated_solution_assets
        if a.get("asset_key") == asset["asset_key"] and a.get("sha256") == digest
    ]
    if len(generated) != 1:
        raise UnsupportedCondition("the prepared SVG must match the current ray PNG")
    new = generated[0]
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    image["data-asset-id"] = new["source_asset_id"]
    image["src"] = new["url"]
    image["alt"] = "График функции из двух лучей"
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
        result,
        transformations=(asset_change, condition_change, *result.transformations),
    )
