"""Events on checksum-verified Euler diagrams; labels are data, not answers."""

import hashlib
import json
import operator
import re
from dataclasses import replace
from fractions import Fraction
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from solution_runner.pipelines.word_problems.common import rewrite, section

from .common import (
    SIGNED,
    UnsupportedCondition,
    finish,
    fmt,
    line,
    number,
    read,
    result,
)

_ASSETS = Path(__file__).with_name("assets")
_EVIDENCE = json.loads((_ASSETS / "euler_evidence.json").read_text())
_PREFIX = r"На диаграмме Эйлера схематически (?P<mode>показан|показали) случайный опыт S, с которым связана случайная величина X\. "
_WEIGHTED = "Около каждого элементарного события указана вероятность этого события и соответствующее значение случайной величины X."
_UNIFORM = "Все элементарные события равновозможны, и около каждого указано соответствующее значение случайной величины X."
_PATTERN = re.compile(
    _PREFIX
    + rf"(?P<description>{re.escape(_WEIGHTED)}|{re.escape(_UNIFORM)}) Найдите вероятность события X(?P<relation>=|\\gt|\\ge|\\lt|\\le)\s*(?P<value>{SIGNED})\."
)
_RELATIONS = {
    "=": operator.eq,
    r"\gt": operator.gt,
    r"\ge": operator.ge,
    r"\lt": operator.lt,
    r"\le": operator.le,
}
_KEY = "generated_euler_event"
_ALT = "Элементарные события, удовлетворяющие условию, обведены зелёным"


def _input(context):
    content = context.get("normalized_content") or {}
    condition = section(content, "condition")
    if condition is None or len(condition.get("asset_keys") or []) != 1:
        raise UnsupportedCondition("one canonical Euler condition image is required")
    key = condition["asset_keys"][0]
    assets = [a for a in content.get("assets", []) if a.get("asset_key") == key]
    if len(assets) != 1 or assets[0].get("asset_id") not in _EVIDENCE:
        raise UnsupportedCondition(
            "the Euler diagram needs a verified mathematical transcription"
        )
    asset = assets[0]
    entry = _EVIDENCE[asset["asset_id"]]
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != asset["asset_id"]
    ):
        raise UnsupportedCondition(
            "the visible Euler image disagrees with its attachment"
        )
    images[0].decompose()
    copied = {**condition, "html": str(soup), "asset_keys": []}
    clean = {
        **context,
        "normalized_content": {
            **content,
            "assets": [],
            "sections": [copied if s is condition else s for s in content["sections"]],
        },
    }
    _, answer, solution, text, tables = read(clean)
    match = _PATTERN.fullmatch(text)
    if (
        tables
        or match is None
        or (match["description"] == _UNIFORM) != entry["uniform"]
    ):
        raise UnsupportedCondition("unsupported complete Euler event condition")
    points = entry["points"]
    weights = [
        Fraction(1, len(points)) if entry["uniform"] else Fraction(p["probability"])
        for p in points
    ]
    if not weights or sum(weights) != 1 or any(p < 0 for p in weights):
        raise UnsupportedCondition(
            "the diagram does not define a probability distribution"
        )
    threshold = number(match["value"])
    predicate = _RELATIONS[match["relation"]]
    indices = [
        i for i, p in enumerate(points) if predicate(Fraction(p["value"]), threshold)
    ]
    source = (_ASSETS / (asset["asset_id"] + ".svg")).read_bytes()
    if hashlib.sha256(source).hexdigest() != entry["sha256"]:
        raise UnsupportedCondition("the audited Euler source template has changed")
    return content, condition, answer, solution, asset, entry, weights, indices, source


def _overlay(entry, indices):
    return next(
        (item for item in entry["overlays"] if item["indices"] == indices), None
    )


def required_assets(context):
    *_, entry, _weights, indices, _source = _input(context)
    overlay = _overlay(entry, indices)
    return (
        (
            {
                "source_asset_id": overlay["asset_id"],
                "section_id": "solution:1",
                "alt_text": _ALT,
            },
        )
        if overlay
        else ()
    )


def annotated_svg(entry, indices, source):
    root = ET.fromstring(source)
    ns = "{http://www.w3.org/2000/svg}"
    ET.register_namespace("", ns[1:-1])
    layer = ET.SubElement(root, ns + "g", {"data-role": "selected-events"})
    for i in indices:
        p = entry["points"][i]
        ET.SubElement(
            layer,
            ns + "ellipse",
            {
                "cx": str(p["x"] - (2.4 if entry["uniform"] else 0)),
                "cy": str(p["y"] - (5 if entry["uniform"] else 2)),
                "rx": "11.998" if entry["uniform"] else "14.5",
                "ry": "15.104" if entry["uniform"] else "18.25",
                "fill": "none",
                "stroke": "#179A48" if entry["uniform"] else "#0A990A",
                "stroke-miterlimit": "10",
                "data-event-index": str(i),
            },
        )
    return ET.tostring(root, encoding="unicode")


def diagram_specs(context):
    *_, entry, _weights, indices, source = _input(context)
    if not indices or _overlay(entry, indices):
        return ()
    svg = annotated_svg(entry, indices, source)
    return (
        {
            "asset_key": _KEY,
            "svg_text": svg,
            "sha256": hashlib.sha256(svg.encode()).hexdigest(),
        },
    )


def _image(content, entry, indices, source, generated):
    if not indices:
        return "", [], []
    overlay = _overlay(entry, indices)
    changes = []
    if overlay:
        asset = next(
            (
                a
                for a in content.get("assets", [])
                if a.get("asset_id") == overlay["asset_id"]
            ),
            None,
        )
        if asset is None:
            raise UnsupportedCondition("the matching solution diagram is required")
        key, asset_id = asset["asset_key"], asset["asset_id"]
        url = asset.get("url") or "/assets/" + asset_id
    else:
        if (
            len(generated) != 1
            or generated[0].get("asset_key") != _KEY
            or generated[0].get("sha256")
            != hashlib.sha256(
                annotated_svg(entry, indices, source).encode()
            ).hexdigest()
        ):
            raise UnsupportedCondition(
                "the prepared annotation does not match the selected events"
            )
        asset = generated[0]
        key, asset_id, url = _KEY, asset["source_asset_id"], asset["url"]
        if not any(
            a.get("asset_key") == key and a.get("asset_id") == asset_id
            for a in content.get("assets", [])
        ):
            changes.append(
                {
                    "transformation_target_id": "asset:" + key,
                    "operation": "add",
                    "value": {
                        "asset_key": key,
                        "asset_id": asset_id,
                        "url": url,
                        "kind": "ordinary_image",
                        "alt": _ALT,
                        "parent_target_id": "section:solution:1",
                        "position": 0,
                    },
                }
            )
    image = f'<center><img alt="{_ALT}" data-asset-key="{escape(key, quote=True)}" data-asset-id="{escape(asset_id, quote=True)}" src="{escape(url, quote=True)}"/></center>'
    if changes:
        changes[0]["value"]["html"] = image
    return image, [key], changes


def build_context_repair_plan(
    context, *, condition_asset_bytes=None, generated_solution_assets=()
):
    (
        content,
        condition,
        answer_section,
        solution,
        _asset,
        entry,
        weights,
        indices,
        source,
    ) = _input(context)
    if (
        not isinstance(condition_asset_bytes, bytes)
        or hashlib.sha256(condition_asset_bytes).hexdigest() != entry["sha256"]
    ):
        raise UnsupportedCondition(
            "the current Euler SVG must match its mathematical transcription"
        )
    image, keys, asset_changes = _image(
        content, entry, indices, source, generated_solution_assets
    )
    selected = [weights[i] for i in indices]
    html = (
        f"<p>Требуемому событию соответствуют {len(indices)} из {len(weights)} элементарных событий."
        + (
            " Они обведены зелёным на рисунке:</p>"
            if indices
            else " На диаграмме нет подходящих значений, поэтому событие невозможно.</p>"
        )
    )
    html += image
    if entry["uniform"]:
        html += (
            "<p>Все элементарные события равновозможны. Вероятность каждого равна:</p>"
            + line(rf"p_i=\frac{{1}}{{{len(weights)}}}")
        )
    html += (
        "<p>Элементарные события несовместны, поэтому сложим их вероятности:</p>"
        + line("P=" + ("+".join(fmt(p) for p in selected) or "0"))
    )
    answer, html = result(sum(selected, Fraction(0)), html, "P")
    repair = finish(condition, answer_section, solution, answer, html)
    changes = list(repair.transformations)
    if (
        not any(
            t["transformation_target_id"].startswith("section:solution")
            for t in changes
        )
        and (solution or {}).get("asset_keys") != keys
    ):
        changes.append(rewrite(solution, "solution", "Решение", html))
    for t in changes:
        if t["transformation_target_id"].startswith("section:solution"):
            t["value"]["asset_keys"] = keys
    return replace(repair, transformations=tuple(asset_changes + changes))
