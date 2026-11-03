"""Native side-altitude examples and their complete-condition reader."""

import json
from pathlib import Path

from solution_runner.pipelines.triangles.isosceles.side_altitude_model import (
    read_question,
)

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_isosceles_altitude_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}
PARENTS = {c["group"]: c for c in CASES if c["task"] == c["group"]}


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


def model(case, context=None):
    ctx = case["context"] if context is None else context
    source = next(
        a["asset_id"]
        for a in ctx["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    return read_question(section(ctx, "condition")["html"], source).require_rule(
        GROUPS[case["group"]]["rule"]
    )
