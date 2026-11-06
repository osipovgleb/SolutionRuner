"""Unmodified native statements for the four final volume and line-angle families."""

import json
from pathlib import Path

from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.solids.spatial_distance_model import condition_text

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_15_volume_sections_sources.json"
    ).read_text()
)

CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def arguments(group):
    ctx = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": None,
        "parent_solution_html": section(ctx, "solution")["html"],
        "parent_solution_assets": _solution_assets(ctx),
    }


def plan(case, context=None, **overrides):
    ctx = case["context"] if context is None else context
    handler = get_handler(GROUPS[case["group"]]["rule"])
    return handler.plan(PlanInput(ctx, **{**arguments(case["group"]), **overrides}))


def raw(task):
    case = next(c for c in CASES if c["task"] == task)
    sections = case["context"]["normalized_content"]["sections"]
    return condition_text(
        next(s["html"] for s in sections if s["key"] == "condition"), None
    )


def replace(task, *pairs):
    text = raw(task)
    for old, new in pairs:
        assert old in text
        text = text.replace(old, new)
    return text
