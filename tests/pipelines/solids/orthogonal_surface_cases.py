"""Native surface source contexts and complete parent bindings."""

import json
from pathlib import Path

from bs4 import BeautifulSoup
from midpoint_source_cases import section
from sphere_formula_oracle import PiParser

from solution_runner.pipelines.core.content_runtime import (
    _condition_asset_id,
    _solution_assets,
)
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.solids.orthogonal_figures import selection

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_orthogonal_surface_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def arguments(group):
    ctx = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": _condition_asset_id(ctx),
        "parent_solution_html": section(ctx, "solution")["html"],
        "parent_solution_assets": _solution_assets(ctx),
    }


def plan(case, context=None, **overrides):
    return get_handler(GROUPS[case["group"]]["rule"]).plan(
        PlanInput(
            case["context"] if context is None else context,
            **{**arguments(case["group"]), **overrides},
        )
    )


def read(case):
    return selection(case["context"], GROUPS[case["group"]]["rule"])


def expected(case):
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    node = soup.select_one("[data-inline-latex]")
    return (
        PiParser(
            case.get(
                "expected_answer",
                node["data-inline-latex"] if node else soup.get_text(strip=True),
            )
        )
        .parse()
        .value
    )
