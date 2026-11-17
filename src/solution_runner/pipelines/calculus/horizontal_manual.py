"""Handwritten sign solutions for the two audited native derivative graphs."""

import hashlib
import json
from pathlib import Path

from bs4 import BeautifulSoup

from ..probability.common import UnsupportedCondition, finish, line
from ..triangles.right.basic_parent import _targeted

DATA = Path(__file__).with_name("assets") / "horizontal-manual-solutions.json"


def canonical(raw):
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup.find_all(True):
        tag.attrs.pop("data-transformation-target-id", None)
    return str(soup)


def supports(context):
    ids = json.loads(DATA.read_text())
    condition = next(
        (
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "condition"
        ),
        {},
    )
    return any(
        a.get("asset_id") in ids
        and a.get("asset_key") in condition.get("asset_keys", [])
        for a in context["normalized_content"]["assets"]
    )


def build(context, data):
    content = context["normalized_content"]
    condition = next(s for s in content["sections"] if s["key"] == "condition")
    assets = [
        a
        for a in content["assets"]
        if a["asset_key"] in condition.get("asset_keys", [])
    ]
    if len(assets) != 1:
        raise UnsupportedCondition(
            "the handwritten solution requires one exact source graph"
        )
    asset = assets[0]
    entry = json.loads(DATA.read_text()).get(asset["asset_id"])
    if (
        entry is None
        or not isinstance(data, bytes)
        or hashlib.sha256(data).hexdigest() != entry["svg_sha256"]
    ):
        raise UnsupportedCondition(
            "the handwritten solution does not match the current graph"
        )
    if (
        hashlib.sha256(canonical(condition["html"]).encode()).hexdigest()
        != entry["condition_sha256"]
    ):
        raise UnsupportedCondition(
            "the handwritten solution does not match the full current question"
        )
    indices = ",".join("x_{" + str(i) + "}" for i in entry["negative_indices"])
    html = '<p>Функция <span data-inline-latex="f(x)"></span> убывает на промежутках, где её производная отрицательна:</p>'
    html += line("f'(x)<0")
    html += (
        '<p>В отмеченных точках <span data-inline-latex="'
        + indices
        + '"></span> график производной расположен ниже оси абсцисс. Таких точек — '
        + entry["answer"]
        + ".</p>"
    )
    return finish(
        condition,
        _targeted(next((s for s in content["sections"] if s["key"] == "answer"), None)),
        _targeted(
            next((s for s in content["sections"] if s["key"] == "solution"), None)
        ),
        entry["answer"],
        canonical(html),
    )
