"""Original cut-cylinder source contexts and preparation bindings."""

import json
from pathlib import Path

from bs4 import BeautifulSoup
from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.solids.cylinder_figures import selection

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_cylinder_cut_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def arguments(group):
    parent = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": parent["normalized_content"]["assets"][0]["asset_id"]
        if parent["normalized_content"]["assets"]
        else None,
        "parent_solution_html": section(parent, "solution")["html"],
        "parent_solution_assets": _solution_assets(parent),
    }


def generated(case, context):
    return tuple(
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(context)
    )


def plan(case, context=None, **overrides):
    ctx = case["context"] if context is None else context
    args = {**arguments(case["group"]), **overrides}
    args.setdefault("generated_solution_assets", generated(case, ctx))
    return get_handler(GROUPS[case["group"]]["rule"]).plan(PlanInput(ctx, **args))


def read(case):
    return selection(case["context"], rule=GROUPS[case["group"]]["rule"])[0]


def saved_answer(case):
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    tag = soup.select_one("[data-inline-latex]")
    return case.get(
        "expected_answer",
        tag["data-inline-latex"] if tag else soup.get_text(strip=True),
    )
