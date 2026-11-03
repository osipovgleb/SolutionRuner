"""Source fixtures and deterministic metadata for area and triangle incircles."""

import json
from pathlib import Path

from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_incircle_triangle_sources.json"
    ).read_text()
)
SOURCE_CASES = DATA["cases"]
CASES = [c for c in SOURCE_CASES if "unsupported_reason" not in c]
REJECTED_CASES = [c for c in SOURCE_CASES if "unsupported_reason" in c]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def arguments(group):
    parent = next(c["context"] for c in CASES if c["task"] == group)
    source = next(
        a["asset_id"]
        for a in parent["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    return {
        "parent_asset_id": source,
        "parent_solution_html": section(parent, "solution")["html"],
        "parent_solution_assets": _solution_assets(parent),
    }


def generated(case, ctx):
    handler = get_handler(GROUPS[case["group"]]["rule"])
    return tuple(
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler.diagram_specs(ctx)
    )


def plan(case, context=None, **overrides):
    ctx = context or case["context"]
    args = {
        **arguments(case["group"]),
        "generated_solution_assets": generated(case, ctx),
        **overrides,
    }
    return get_handler(GROUPS[case["group"]]["rule"]).plan(PlanInput(ctx, **args))


def read(context):
    from solution_runner.pipelines.circles.incircle_model import (
        read_question,
    )

    condition = section(context, "condition")
    source = next(
        (
            a["asset_id"]
            for a in context["normalized_content"]["assets"]
            if a["asset_key"] in condition["asset_keys"]
        ),
        None,
    )
    return read_question(condition["html"], source)
