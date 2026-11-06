"""Reuse certified numerical charts or prepare source-style local replacements."""

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from ..probability import solution_diagrams
from ..probability.common import UnsupportedCondition
from .rational_inequality import analyze
from .rational_inequality_methods import prepare
from .rational_inequality_svg import render

DIRECTORY = Path(__file__).parent / "assets/rational-inequalities"
SOURCES = json.loads((DIRECTORY / "sources.json").read_text())
KEY = "rational_sign_chart"
ALT = "Метод интервалов и ограничения исходных знаменателей"


def read(context):
    content, condition, answer, solution, text = solution_diagrams.read(context)
    spans = BeautifulSoup(condition["html"], "html.parser").find_all(
        "span", attrs={"data-inline-latex": True}
    )
    if len(spans) != 1:
        raise UnsupportedCondition("one explicit inequality formula is required")
    formula = spans[0]["data-inline-latex"]
    if not re.fullmatch(
        r"Решите неравенство:\s*" + re.escape(formula) + r"\s*\.?", text
    ):
        raise UnsupportedCondition(
            "the entire rational inequality instruction must be recognized"
        )
    return (content, condition, answer, solution), analyze(formula)


def signature(a):
    return {
        "points": list(map(str, a.points)),
        "poles": list(map(str, a.poles)),
        "signs": list(a.signs),
        "operator": a.sign_operator,
    }


def selection(context, a, *, required=False):
    assets = context["normalized_content"].get("assets", [])
    originals = [asset for asset in assets if asset.get("asset_key") != KEY]
    generated = [asset for asset in assets if asset.get("asset_key") == KEY]
    if len(originals) > 1 or len(generated) > 1:
        raise UnsupportedCondition(
            "at most one source chart and one prepared chart are supported"
        )
    if originals:
        asset = originals[0]
        entry = SOURCES["figures"].get(asset.get("asset_id"))
        if (
            entry is None
            or asset.get("asset_key") != "image_1"
            or asset.get("kind") != "ordinary_image"
            or asset.get("url") != "/assets/" + asset["asset_id"]
        ):
            raise UnsupportedCondition(
                "the source chart identity is outside visual review"
            )
        if all(entry[key] == value for key, value in signature(a).items()):
            if generated:
                raise UnsupportedCondition(
                    "a compatible chart needs no generated duplicate"
                )
            return asset["asset_id"], None
        return None, render(a, double=required or entry["double"])
    if required or generated:
        return None, render(a, double=required)
    return None, None


def diagram_specs(context):
    _, a = read(context)
    _, svg = selection(context, a)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def cancelled_diagram_specs(context):
    _, a = read(context)
    prepare(a, "cancelled_fraction")
    _, svg = selection(context, a, required=True)
    return (solution_diagrams.spec(KEY, svg),) if svg is not None else ()


def image(context, a, generated, *, required=False):
    source_id, svg = selection(context, a, required=required)
    if source_id is None and svg is None:
        if generated:
            raise UnsupportedCondition(
                "an unrequested rational chart must not be injected"
            )
        return "", (), []
    if source_id is not None and generated:
        raise UnsupportedCondition("the compatible source chart must be reused exactly")
    markup, key, changes = solution_diagrams.image(
        context["normalized_content"],
        KEY,
        ALT,
        source_id=source_id,
        svg=svg,
        generated=generated,
    )
    return markup, (key,), changes


GROUPS = (
    (
        "508440",
        "0d1fc6df-0af1-476a-97dc-288e21a9c5cd",
        1,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "sum_fractions",
    ),
    (
        "508518",
        "0cc30461-8d0e-45e1-81f0-bbaa38fa4237",
        2,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "cancelled_fraction",
    ),
    (
        "508524",
        "161b9b2b-6043-487b-8c9e-ae6524a655f0",
        3,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "direct_fraction",
    ),
    (
        "511560",
        "f4cce06a-c452-48b5-9aa6-ae6b57a3b13d",
        4,
        "Рациональные неравенства",
        1,
        "9c619907-5d8d-437c-b7dd-004b50ba3536",
        "long_division",
    ),
)
