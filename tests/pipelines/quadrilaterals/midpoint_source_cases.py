"""Recorded native contexts and pure preparation helpers for four source methods."""

import json
from pathlib import Path

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_midpoint_area_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}


def section(context, key):
    return next(
        (s for s in context["normalized_content"]["sections"] if s["key"] == key), None
    )


def parent_arguments(group):
    parent = next(c["context"] for c in CASES if c["task"] == group)
    asset = next(
        a["asset_id"]
        for a in parent["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    return {
        "parent_asset_id": asset,
        "parent_solution_html": section(parent, "solution")["html"],
        "parent_solution_assets": _solution_assets(parent),
    }


def generated(case, context=None):
    handler = get_handler(GROUPS[case["group"]]["rule"])
    return tuple(
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler.diagram_specs(context or case["context"])
    )


def plan(case, context=None, **overrides):
    args = {**parent_arguments(case["group"]), **overrides}
    ctx = context or case["context"]
    args.setdefault("generated_solution_assets", generated(case, ctx))
    return get_handler(GROUPS[case["group"]]["rule"]).plan(PlanInput(ctx, **args))


def solution_html(result):
    return next(
        t["value"]["html"]
        for t in result.transformations
        if t["transformation_target_id"].startswith("section:solution")
    )


def replay(context, changes):
    content = context["normalized_content"]
    for change in changes:
        target = change["transformation_target_id"]
        if target.startswith("asset:"):
            key = target.removeprefix("asset:")
            current = next(
                (a for a in content["assets"] if a["asset_key"] == key), None
            )
            if change["operation"] == "remove":
                content["assets"].remove(current)
            elif current is not None:
                current.update(change["value"])
            else:
                content["assets"].append(dict(change["value"]))
        else:
            key = target.split(":")[1]
            current = section(context, key)
            if current is None:
                current = {
                    "key": key,
                    "transformation_target_id": "section:" + key + ":1",
                }
                content["sections"].append(current)
            current.update(change["value"])
