"""Select reviewed local circles by complete equation and interval, without IDs."""

import json
from copy import deepcopy
from pathlib import Path

import sympy as sp

from ..word_problems.common import UnsupportedCondition
from .exam_input import read
from .power_arithmetic import clean

DIRECTORY = Path(__file__).parent / "assets/exam-trigonometry"
RECIPES = json.loads((DIRECTORY / "prepared-circles.json").read_text())


def source_less(context):
    content = context.get("normalized_content") or {}
    return all(
        a.get("asset_key") == "exam_trig_circle" for a in content.get("assets", [])
    )


def recipe(context):
    prepared = deepcopy(context)
    content = prepared.get("normalized_content") or {}
    assets = content.get("assets", [])
    if not source_less(context):
        return None
    if len(assets) > 1 or any(
        not isinstance(a.get("asset_id"), str)
        or not a["asset_id"]
        or a.get("kind") != "ordinary_image"
        or a.get("url") != "/assets/" + str(a.get("asset_id", ""))
        for a in assets
    ):
        raise UnsupportedCondition(
            "one prepared solution circle with its exact identity is required"
        )
    content["assets"] = []
    for section in content.get("sections", []):
        if section.get("key") == "solution":
            section["asset_keys"] = []
    _, formula, _, bounds = read(prepared)
    from .exam_trigonometric_inverse import decode

    for entry in RECIPES:
        expected = tuple(decode(q) for q in entry["bounds"][:2]) + tuple(
            entry["bounds"][2:]
        )
        actual = tuple(q / sp.pi for q in bounds[:2]) + bounds[2:]
        if (
            clean(formula).removesuffix(".") == clean(entry["formula"])
            and actual == expected
        ):
            return entry
    return None
