"""An opt-in area runner: rebuild current PNG parabolas; retain original SVGs.

Conversion is deterministic and is executed during ordinary prepare/apply. It
never downloads from a planner or reads an archive of pre-generated SVG files.
"""

import hashlib
from copy import deepcopy

import sympy as sp
from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition, finish, rewrite
from ..triangles.right.basic_parent import _targeted
from . import graph_input, graph_integrals, parabola_proof, raster_parabola
from .common import X, answer

# Visually reviewed original SVG: boundaries 9 and 11, positive bowl.
# This evidence only enables its maths; the native SVG is never rebuilt.
_NATIVE_BOWL_SHA256 = "ab897d6739f73611d29514b24b2deb09517612a362511a6e0d0a47815b4dfd41"


def _text_data(context):
    prepared = deepcopy(context)
    content = prepared["normalized_content"]
    conditions = [s for s in content["sections"] if s.get("key") == "condition"]
    if len(conditions) != 1:
        raise UnsupportedCondition("one complete parabola condition is required")
    condition = conditions[0]
    if len(condition.get("asset_keys", [])) != 1:
        raise UnsupportedCondition("one parabola condition image is required")
    key = condition["asset_keys"][0]
    assets = [a for a in content["assets"] if a.get("asset_key") == key]
    if len(assets) != 1 or assets[0].get("kind") != "ordinary_image":
        raise UnsupportedCondition("the condition graph metadata is ambiguous")
    asset = assets[0]
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-id") != asset["asset_id"]
        or images[0].get("data-asset-key") != key
    ):
        raise UnsupportedCondition("the visible parabola does not match its asset")
    images[0].decompose()
    condition["html"] = str(soup)
    condition["asset_keys"] = []
    content["assets"] = []
    text = graph_input._read_text(prepared)[4]
    question = graph_integrals.parse(text)
    if question.operation != "area":
        raise UnsupportedCondition(
            "the raster parabola runner requires the shaded area question"
        )
    original = context["normalized_content"]
    return (
        question,
        next(s for s in original["sections"] if s.get("key") == "condition"),
        asset,
    )


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


def _converted(context, data):
    if not isinstance(data, bytes) or not data.startswith(raster_parabola.PNG):
        raise UnsupportedCondition(
            "PNG bytes are required for dynamic parabola conversion"
        )
    question, condition, asset = _text_data(context)
    if len(context["normalized_content"]["assets"]) != 1:
        raise UnsupportedCondition(
            "unrelated raster parabola assets need separate review"
        )
    model = raster_parabola.recover(data, question.primitive)
    svg, entry = raster_parabola.render(model)
    return question, condition, asset, model, svg, entry


def diagram_specs(context, *, condition_asset_bytes=None):
    if isinstance(condition_asset_bytes, bytes) and condition_asset_bytes.startswith(
        raster_parabola.PNG
    ):
        _, _, asset, _, svg, _ = _converted(context, condition_asset_bytes)
        return (solution_diagrams.spec(asset["asset_key"], svg),)
    return ()


def _area(question, entry):
    f = sp.diff(question.primitive, X)
    p = sp.Poly(f, X)
    if (
        p.degree() != 2
        or [str(c) for c in p.all_coeffs()] != entry["derivative_coefficients"]
    ):
        raise UnsupportedCondition(
            "the generated parabola disagrees with the condition"
        )
    lower, upper = map(sp.Rational, entry["area_span"])
    center = -p.nth(1) / (2 * p.nth(2))
    height = f.subs(X, center)
    checks = [f.subs(X, lower), f.subs(X, upper)]
    if lower <= center <= upper:
        checks.append(height)
    if lower >= upper or min(checks) < 0:
        raise UnsupportedCondition(
            "the shaded interval must be ordered and above the axis"
        )
    if p.nth(2) < 0 and (f.subs(X, lower) != 0 or f.subs(X, upper) != 0):
        raise UnsupportedCondition("the shaded cap must end at both exact roots")
    result = sp.simplify(
        question.primitive.subs(X, upper) - question.primitive.subs(X, lower)
    )
    if result <= 0:
        raise UnsupportedCondition("the exact shaded area must be positive")
    return graph_integrals.QuadraticArea(
        lower, upper, question.primitive, f, center, p.nth(2), height, result
    )


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    data = condition_asset_bytes
    if not isinstance(data, bytes):
        raise UnsupportedCondition("the current graph bytes are required")
    if not data.startswith(raster_parabola.PNG):
        question, condition, asset = _text_data(context)
        entry = raster_parabola.embedded(data, question.primitive)
        if entry is None and hashlib.sha256(data).hexdigest() == _NATIVE_BOWL_SHA256:
            entry = {
                "derivative_coefficients": ["6", "-120", "601"],
                "area_span": ["9", "11"],
                "area_kind": "bowl",
            }
        if entry is None:
            # Retain the existing SVG validation and mathematical reader.
            # Only the solution presentation is replaced for these two groups.
            graph_integrals.build_context_repair_plan(
                context, condition_asset_bytes=data
            )
            _, _, model = graph_integrals.calculate(context)
        else:
            model = _area(question, entry)
        content = context["normalized_content"]
        return finish(
            condition,
            _targeted(
                next((s for s in content["sections"] if s["key"] == "answer"), None)
            ),
            _targeted(
                next((s for s in content["sections"] if s["key"] == "solution"), None)
            ),
            answer(model.result),
            parabola_proof.endpoint_values(model),
        )
    question, condition, asset, _, svg, entry = _converted(context, data)
    model = _area(question, entry)
    digest = hashlib.sha256(svg.encode()).hexdigest()
    generated = [
        a
        for a in generated_solution_assets
        if a.get("asset_key") == asset["asset_key"] and a.get("sha256") == digest
    ]
    if len(generated) != 1:
        raise UnsupportedCondition(
            "the prepared SVG must match the current PNG and formula"
        )
    new = generated[0]
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    image["data-asset-id"] = new["source_asset_id"]
    image["src"] = new["url"]
    image["data-transformation-target-id"] = "asset:" + asset["asset_key"]
    image["alt"] = "График параболы и заданная закрашенная область"
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
    content = context["normalized_content"]
    result = finish(
        condition,
        _targeted(next((s for s in content["sections"] if s["key"] == "answer"), None)),
        _targeted(
            next((s for s in content["sections"] if s["key"] == "solution"), None)
        ),
        answer(model.result),
        parabola_proof.endpoint_values(model),
    )
    from dataclasses import replace

    return replace(
        result,
        transformations=(asset_change, condition_change, *result.transformations),
    )
