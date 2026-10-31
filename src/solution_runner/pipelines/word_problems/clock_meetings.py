"""Strictly future meetings of clock hands, with the inspected source figure."""

import re
from copy import deepcopy
from dataclasses import dataclass

import sympy as sp
from bs4 import BeautifulSoup

from ..calculus.common import answer
from ..probability import solution_diagrams as diagrams
from . import math_common
from .common import UnsupportedCondition

_ORDINALS = (
    "первый",
    "второй",
    "третий",
    "четвертый",
    "пятый",
    "шестой",
    "седьмой",
    "восьмой",
    "девятый",
    "десятый",
    "одиннадцатый",
    "двенадцатый",
)
_PATTERN = re.compile(
    r"Часы со стрелками показывают (?P<h>\d+) час(?:а|ов)?(?: ровно| (?P<m>\d+) минут(?:а|ы)?)\. Через сколько минут минутная стрелка в (?P<n>"
    + "|".join(_ORDINALS)
    + r"|\d+-й) раз поравняется с часовой\?"
)
ASSET_ID = "26f75a6a-bbac-4512-baed-fa8e1deb316f"
ASSET_SHA256 = "d502e3824345a2e63f4fe3efaf0ac56ee7168eae1e81f0cffedcaab3a171d0c2"


@dataclass(frozen=True)
class Question:
    hour: int
    minute: int
    count: int


def parse(text):
    match = _PATTERN.fullmatch(text)
    if not match:
        raise UnsupportedCondition(
            "the complete clock-hand meeting question must be recognized"
        )
    hour, minute = int(match["h"]), int(match["m"] or "0")
    count = (
        _ORDINALS.index(match["n"]) + 1
        if match["n"] in _ORDINALS
        else int(match["n"][:-2])
    )
    if not 0 <= hour < 24 or not 0 <= minute < 60 or count < 1:
        raise UnsupportedCondition(
            "valid clock time and a positive future meeting number are required"
        )
    return Question(hour % 12, minute, count)


@dataclass(frozen=True)
class Analysis:
    question: Question
    angle: sp.Rational
    first: sp.Rational
    interval: sp.Rational
    result: sp.Rational


def analyze(q):
    angle = sp.Rational(60 * q.hour - 11 * q.minute, 2) % 360
    if angle == 0:
        angle = sp.Integer(360)
    first, interval = 2 * angle / 11, sp.Rational(720, 11)
    return Analysis(q, angle, first, interval, first + (q.count - 1) * interval)


def figure(content, q):
    assets = content.get("assets", [])
    if not isinstance(assets, list) or any(not isinstance(a, dict) for a in assets):
        raise UnsupportedCondition("canonical clock asset metadata is required")
    sections = content.get("sections", [])
    if any(s.get("asset_keys") for s in sections if s.get("key") != "solution"):
        raise UnsupportedCondition("the clock figure may appear only in the solution")
    solution = next((s for s in sections if s.get("key") == "solution"), {})
    soup = BeautifulSoup(solution.get("html", ""), "html.parser")
    images = soup.select("img, [data-asset-id], [data-asset-key], [href*='/assets/']")
    if not assets:
        if images or solution.get("asset_keys"):
            raise UnsupportedCondition(
                "clock figure references must have audited metadata"
            )
        return "", ()
    if len(assets) != 1 or (q.hour, q.minute) != (1, 35):
        raise UnsupportedCondition(
            "the inspected clock figure is compatible only with 1:35"
        )
    asset = assets[0]
    key = asset.get("asset_key")
    if not isinstance(key, str) or not key:
        raise UnsupportedCondition("a nonempty clock asset key is required")
    if (
        asset.get("asset_id") != ASSET_ID
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != "/assets/" + ASSET_ID
    ):
        raise UnsupportedCondition(
            "the exact inspected clock asset identity is required"
        )
    if solution.get("asset_keys") != [key] or len(images) != 1:
        raise UnsupportedCondition("one canonical clock figure reference is required")
    image = images[0]
    if (
        image.name != "img"
        or image.get("data-asset-id") != ASSET_ID
        or image.get("data-asset-key") != key
        or image.get("src") != asset["url"]
    ):
        raise UnsupportedCondition("the clock image reference must match its metadata")
    markup, key, changes = diagrams.image(
        content, key, asset.get("alt", ""), source_id=ASSET_ID
    )
    if changes:
        raise UnsupportedCondition(
            "the clock figure must be reused without asset changes"
        )
    return markup, (key,)


def calculate(context):
    prepared = deepcopy(context)
    content = prepared.get("normalized_content")
    if (
        not isinstance(content, dict)
        or not isinstance(content.get("sections"), list)
        or any(not isinstance(s, dict) for s in content["sections"])
    ):
        raise UnsupportedCondition("normalized clock sections are required")
    content["assets"] = []
    for section in content["sections"]:
        if section.get("key") == "solution":
            section["asset_keys"] = []
    data = math_common.read(prepared)
    a = analyze(parse(data[3]))
    markup, keys = figure(context["normalized_content"], a.question)
    return data, a, markup, keys


def build_context_repair_plan(context):
    from .clock_proof import proof

    data, a, markup, keys = calculate(context)
    condition, ans, _, _ = data
    solution = next(
        (
            s
            for s in context["normalized_content"]["sections"]
            if s["key"] == "solution"
        ),
        None,
    )
    return diagrams.repair(
        condition, ans, solution, answer(a.result), proof(a, markup), keys
    )
