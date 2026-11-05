"""Original combination contexts, parent bindings and exact independently saved answers."""

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
from solution_runner.pipelines.solids.combined_figures import selection

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_3_combined_sources.json").read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def question(case):
    html = section(case["context"], "condition")["html"]
    image = BeautifulSoup(html, "html.parser").find("img")
    return html, image["data-asset-id"] if image else None


def expected(case):
    if "expected_answer" in case:
        return PiParser(case["expected_answer"]).parse().value
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    formula = soup.select_one("[data-inline-latex]")
    return (
        PiParser(formula["data-inline-latex"] if formula else soup.get_text(strip=True))
        .parse()
        .value
    )


def arguments(group):
    parent = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": _condition_asset_id(parent),
        "parent_solution_html": section(parent, "solution")["html"],
        "parent_solution_assets": _solution_assets(parent),
    }


def plan(case, context=None, **overrides):
    args = {**arguments(case["group"]), **overrides}
    return get_handler(GROUPS[case["group"]]["rule"]).plan(
        PlanInput(case["context"] if context is None else context, **args)
    )


def read(case):
    return selection(case["context"], GROUPS[case["group"]]["rule"])[0]
