"""Read complete orthogonal element fixtures and their reviewed parent constructions."""

import json
from pathlib import Path

from solution_runner.pipelines.core.content_runtime import (
    _condition_asset_id,
    _generated_diagram_assets,
    _solution_assets,
)
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.solids.orthogonal_element_model import read
from solution_runner.pipelines.solids.orthogonal_element_sources import DATA

FIXTURE = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_orthogonal_element_sources.json"
    ).read_text()
)
CASES = FIXTURE["cases"]
BOUND = [c for c in CASES if "pending_reason" not in c]
PENDING = [c for c in CASES if "pending_reason" in c]
GROUPS = {g["key"]: g for g in FIXTURE["groups"]}


def arguments(group):
    parent = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": _condition_asset_id(parent),
        "parent_solution_html": next(
            s["html"]
            for s in parent["normalized_content"]["sections"]
            if s["key"] == "solution"
        ),
        "parent_solution_assets": _solution_assets(parent),
    }


def plan(case, context=None, **overrides):
    ctx = case["context"] if context is None else context
    handler = get_handler(GROUPS[case["group"]]["rule"])
    generated = _generated_diagram_assets(
        None, ctx, handler.diagram_specs(ctx), case["task"]
    )
    return handler.plan(
        PlanInput(
            ctx,
            **{
                **arguments(case["group"]),
                "generated_solution_assets": generated,
                **overrides,
            },
        )
    )


def model(case):
    review = DATA["proofs"][
        case["source"] + ":" + case["mode"] + ":" + case["requested"]
    ]
    return read(case["source"], case["mode"], case["requested"], review["method"])
