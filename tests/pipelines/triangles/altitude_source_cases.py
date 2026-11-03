"""Shared native altitude fixtures and public-handler preparation for source tests."""

import json
from pathlib import Path

from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_1_altitude_sources.json").read_text()
)
GROUPS = {g["key"]: g for g in DATA["groups"]}
CASES = DATA["cases"]
SUPPORTED = [c for c in CASES if c["status"] == "supported"]
PARENTS = {c["group"]: c for c in CASES if c["group"] == c["task"]}


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


def plan(case, context=None, parent=None):
    group = GROUPS[case["group"]]
    return get_handler("right-triangle-altitude-universal").plan(
        PlanInput(
            context or case["context"],
            parent_asset_id=group["condition_asset_id"],
            parent_solution_html=parent
            if parent is not None
            else section(PARENTS[case["group"]]["context"], "solution")["html"],
        )
    )


def solution_html(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
