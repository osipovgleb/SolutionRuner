"""Native basic-triangle fixtures and preparation through existing handler keys."""

import json
from pathlib import Path

from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_1_basic_right_sources.json").read_text()
)
GROUPS = {g["key"]: g for g in DATA["groups"]}
CASES = DATA["cases"]
PARENTS = {c["group"]: c for c in CASES if c["group"] == c["task"]}


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


def parent_html(group):
    return section(PARENTS[group]["context"], "solution")["html"]


def plan(case, context=None, parent=None):
    group = GROUPS[case["group"]]
    return get_handler(group["rule"]).plan(
        PlanInput(
            context if context is not None else case["context"],
            parent_asset_id=group["parent_asset"],
            parent_solution_html=parent_html(case["group"])
            if parent is None
            else parent,
        )
    )


def solution_html(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )
