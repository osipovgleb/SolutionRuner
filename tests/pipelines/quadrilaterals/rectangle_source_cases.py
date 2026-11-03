"""Recorded rectangle contexts and registered pure planner invocations."""

import json
from pathlib import Path

from midpoint_source_cases import section

from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_1_rectangle_sources.json").read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def arguments(group):
    parent = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": parent["normalized_content"]["assets"][0]["asset_id"],
        "parent_solution_html": section(parent, "solution")["html"],
    }


def plan(case, context=None, **overrides):
    return get_handler(GROUPS[case["group"]]["rule"]).plan(
        PlanInput(
            context or case["context"], **{**arguments(case["group"]), **overrides}
        )
    )
