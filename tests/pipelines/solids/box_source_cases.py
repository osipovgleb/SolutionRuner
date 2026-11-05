"""Recorded rectangular-box contexts and pure preparation helpers."""

import json
from pathlib import Path

from bs4 import BeautifulSoup
from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.solids.box_figures import selection

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_box_measurement_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def arguments(group):
    parent = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": parent["normalized_content"]["assets"][0]["asset_id"],
        "parent_solution_html": section(parent, "solution")["html"],
        "parent_solution_assets": _solution_assets(parent),
    }


def plan(case, context=None, **overrides):
    ctx = case["context"] if context is None else context
    return get_handler(GROUPS[case["group"]]["rule"]).plan(
        PlanInput(ctx, **{**arguments(case["group"]), **overrides})
    )


def read(case):
    return selection(case["context"])[0]


def saved_answer(case):
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    return case.get(
        "expected_answer",
        tag["data-inline-latex"] if tag else soup.get_text(strip=True),
    )
