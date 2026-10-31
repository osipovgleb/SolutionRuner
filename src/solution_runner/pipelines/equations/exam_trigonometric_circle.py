"""Reuse audited circle geometry and labels; prepare the one corrected source SVG."""

import json
from copy import deepcopy
from pathlib import Path

import sympy as sp

from ..probability import solution_diagrams
from ..word_problems.common import UnsupportedCondition, section
from .exam_input import read as read_exam

DIRECTORY = Path(__file__).parent / "assets/exam-trigonometry"
CIRCLES = json.loads((DIRECTORY / "source-circles.json").read_text())
KEY = "exam_trig_circle"


def source(context):
    content = context.get("normalized_content") or {}
    assets = content.get("assets", [])
    generated = [a for a in assets if a.get("asset_key") == KEY]
    originals = [a for a in assets if a.get("asset_key") != KEY]
    if (
        len(originals) != 1
        or len(generated) > 1
        or originals[0].get("asset_id") not in CIRCLES
    ):
        raise UnsupportedCondition(
            "one mathematically audited source circle is required"
        )
    asset = originals[0]
    entry = CIRCLES[asset["asset_id"]]
    if (
        asset.get("asset_key") != "image_1"
        or asset.get("url") != "/assets/" + asset["asset_id"]
        or asset.get("kind") != "ordinary_image"
    ):
        raise UnsupportedCondition("the original circle identity changed")
    if generated and not entry.get("corrected_file"):
        raise UnsupportedCondition(
            "an unneeded generated circle must not replace a compatible source"
        )
    return asset, entry


def read(context):
    if not (context.get("normalized_content") or {}).get("assets"):
        return read_exam(context)
    source(context)
    content = context["normalized_content"]
    prepared = deepcopy(context)
    prepared["normalized_content"]["assets"] = []
    copied_solution = section(prepared["normalized_content"], "solution")
    if copied_solution is not None:
        copied_solution["asset_keys"] = []
    _parts, formula, interval, bounds = read_exam(prepared)
    return (
        tuple(section(content, key) for key in ("condition", "answer", "solution")),
        formula,
        interval,
        bounds,
    )


def validate(entry, a):
    from .exam_trigonometric_inverse import decode

    expected = tuple(decode(q) for q in entry["residues"])
    bounds = tuple(sp.Rational(q) for q in entry["bounds"][:2]) + tuple(
        entry["bounds"][2:]
    )
    labels = tuple(decode(q) for q in entry["labels"])
    if a.residues != expected or a.bounds != bounds or a.selected != labels:
        raise UnsupportedCondition(
            "the circle points, interval and labels must match the computed equation exactly"
        )


def diagram_specs(context):
    if not (context.get("normalized_content") or {}).get("assets"):
        return ()
    _, entry = source(context)
    if not entry.get("corrected_file"):
        return ()
    return (
        solution_diagrams.spec(KEY, (DIRECTORY / entry["corrected_file"]).read_text()),
    )


def image(context, a, generated):
    if not context["normalized_content"].get("assets"):
        if a.selection_method != "inequalities":
            raise UnsupportedCondition("circle selection requires its source figure")
        return "", "", []
    asset, entry = source(context)
    validate(entry, a)
    if entry.get("corrected_file"):
        return solution_diagrams.image(
            context["normalized_content"],
            KEY,
            "Окружность для отбора корней",
            svg=(DIRECTORY / entry["corrected_file"]).read_text(),
            generated=generated,
        )
    return solution_diagrams.image(
        context["normalized_content"],
        "image_1",
        "Окружность для отбора корней",
        source_id=asset["asset_id"],
    )
