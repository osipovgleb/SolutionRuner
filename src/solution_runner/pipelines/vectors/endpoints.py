"""Endpoint coordinates from a displacement, preserving compatible auxiliary figures."""

import json
import re
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import (
    format_answer,
    format_latex_fraction,
    parse_rational,
)
from solution_runner.pipelines.probability import condition_diagram
from solution_runner.pipelines.probability.common import (
    UnsupportedCondition,
    finish,
    line,
)
from solution_runner.pipelines.probability.solution_diagrams import spec
from solution_runner.pipelines.statistics.common import read as read_plain
from solution_runner.pipelines.vectors.planner import _asset_html, _asset_transformation
from solution_runner.pipelines.word_problems.common import rewrite

_ASSETS = Path(__file__).with_name("assets")
_EVIDENCE = json.loads((_ASSETS / "endpoint_diagrams.json").read_text())
_PAIR = r"\([\d+−–,;.{}\s-]+\)"
_PATTERN = re.compile(
    rf"Вектор \\overrightarrow\{{(?P<tail>[A-Z])(?P<head>[A-Z])\}} с (?P<kind>началом|концом) в точке (?P<given>[A-Z])\s*(?P<point>{_PAIR})\s*имеет координаты\s*(?P<vector>{_PAIR})\. Найдите (?P<mode>абсциссу|ординату|сумму координат) точки (?P<target>[A-Z])\."
)


def pair(text):
    if len(text) > 200:
        raise UnsupportedCondition("the coordinate pair is too long")
    text = text[1:-1].replace("−", "-").replace("–", "-").replace("{,}", ",")
    parts = text.split(";" if ";" in text else ",")
    if len(parts) != 2:
        raise UnsupportedCondition("two unambiguous planar coordinates are required")
    return tuple(parse_rational(p.strip()) for p in parts)


def endpoint(known, displacement, *, given_start):
    return tuple(
        p + v if given_start else p - v
        for p, v in zip(known, displacement, strict=True)
    )


def diagram_specs(context):
    assets = (context.get("normalized_content") or {}).get("assets", [])
    if len(assets) != 1:
        return ()
    asset = assets[0]
    for source_id, entry in _EVIDENCE.items():
        correction = entry.get("correction")
        if correction and (
            asset.get("asset_id") == source_id or asset.get("alt") == correction["alt"]
        ):
            svg = (_ASSETS / correction["filename"]).read_text()
            prepared = spec(asset["asset_key"], svg)
            if prepared["sha256"] != correction["sha256"]:
                raise UnsupportedCondition("the corrected endpoint diagram has changed")
            return (prepared,)
    return ()


def _read(context, generated):
    content = context.get("normalized_content") or {}
    condition = next(
        (s for s in content.get("sections", []) if s.get("key") == "condition"), None
    )
    if condition and condition.get("asset_keys"):
        evidence = dict(_EVIDENCE)
        for entry in _EVIDENCE.values():
            correction = entry.get("correction")
            if correction:
                for asset in generated:
                    if (
                        asset.get("sha256") == correction["sha256"]
                        and asset.get("asset_key") == "image_1"
                    ):
                        evidence[asset["source_asset_id"]] = {**entry, **correction}
        content, condition, answer, solution, text, entry, _source = (
            condition_diagram.read(context, evidence, _ASSETS)
        )
        if len(content.get("assets", [])) != 1:
            raise UnsupportedCondition(
                "only one audited auxiliary endpoint diagram is supported"
            )
        return condition, answer, solution, text, entry
    condition, answer, solution, text, tables = read_plain(context)
    if tables:
        raise UnsupportedCondition(
            "coordinate declarations cannot contain an unparsed table"
        )
    return condition, answer, solution, text, None


def _correct_diagram(context, condition, entry, generated, plan):
    if not entry or not entry.get("correction"):
        return plan
    correction = entry["correction"]
    specs = diagram_specs(context)
    matches = [
        a
        for a in generated
        if a.get("sha256") == correction["sha256"] and a.get("asset_key") == "image_1"
    ]
    if len(specs) != 1 or len(matches) != 1:
        raise UnsupportedCondition(
            "the corrected condition diagram must be prepared first"
        )
    asset_id = matches[0]["source_asset_id"]
    soup = BeautifulSoup(condition["html"], "html.parser")
    image = soup.find("img")
    if image["data-asset-id"] == asset_id:
        return plan
    image.replace_with(
        BeautifulSoup(_asset_html(asset_id, correction["alt"]), "html.parser")
    )
    html = str(soup)
    change = rewrite(condition, "condition", "Условие", html)
    change["value"]["asset_keys"] = condition["asset_keys"]
    return replace(
        plan,
        condition_html=html,
        transformations=(
            _asset_transformation(asset_id, correction["alt"], replace=True),
            change,
            *plan.transformations,
        ),
    )


def build_context_repair_plan(context, *, generated_solution_assets=()):
    condition, answer_section, solution, text, entry = _read(
        context, generated_solution_assets
    )
    match = _PATTERN.fullmatch(text)
    if match is None:
        raise UnsupportedCondition("unsupported complete endpoint-coordinate condition")
    tail, head = match["tail"], match["head"]
    given_start = match["kind"] == "началом"
    given, target = (tail, head) if given_start else (head, tail)
    if tail == head or match["given"] != given or match["target"] != target:
        raise UnsupportedCondition(
            "the named known and requested endpoints must agree with the vector direction"
        )
    known, displacement = pair(match["point"]), pair(match["vector"])
    calculated = endpoint(known, displacement, given_start=given_start)
    endpoints = (known, calculated) if given_start else (calculated, known)
    if entry and (
        entry["names"] != [tail, head]
        or tuple(tuple(Fraction(x) for x in p) for p in entry["points"]) != endpoints
    ):
        raise UnsupportedCondition(
            "the auxiliary diagram is incompatible with the explicit endpoint coordinates"
        )
    f = format_latex_fraction
    html = "<p>Координаты вектора равны разности соответствующих координат его конца и начала:</p>"
    html += line(
        rf"\overrightarrow{{{tail}{head}}}=(x_{{{head}}}-x_{{{tail}}};y_{{{head}}}-y_{{{tail}}})"
    )
    html += f"<p>Пусть неизвестная точка {target} имеет координаты (x; y). Подставим известную точку и координаты вектора:</p>"
    equations = [
        (axis, coordinate, delta, value)
        for axis, coordinate, delta, value in zip(
            ("x", "y"), known, displacement, calculated, strict=True
        )
    ]
    for axis, coordinate, delta, value in equations:
        left = (
            rf"{axis}_{{{target}}}-({f(coordinate)})"
            if given_start
            else rf"({f(coordinate)})-{axis}_{{{target}}}"
        )
        html += line(left + "=" + f(delta))
        html += line(
            rf"{axis}_{{{target}}}=({f(coordinate)})"
            + ("+" if given_start else "-")
            + "("
            + f(delta)
            + ")="
            + f(value)
        )
    mode = match["mode"]
    if mode == "сумму координат":
        value = sum(calculated)
        html += "<p>Сложим координаты найденной точки:</p>" + line(
            rf"x_{{{target}}}+y_{{{target}}}=({f(calculated[0])})+({f(calculated[1])})={f(value)}"
        )
    else:
        value = calculated[0 if mode == "абсциссу" else 1]
    plan = finish(condition, answer_section, solution, format_answer(value), html)
    return _correct_diagram(context, condition, entry, generated_solution_assets, plan)
