"""Native construction triangle source cases and public handler preparation."""

import json
from pathlib import Path

from solution_runner.pipelines.core.content_runtime import _generated_diagram_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput

DATA = json.loads(
    (Path(__file__).parent / "fixtures/category_1_two_ray_sources.json").read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}
PARENTS = {c["group"]: c for c in CASES if c["task"] == c["group"]}


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


def parent_html(group):
    return section(PARENTS[group]["context"], "solution")["html"]


def plan(case, context=None, parent=None):
    group = GROUPS[case["group"]]
    return get_handler(group["rule"]).plan(
        PlanInput(
            context if context is not None else case["context"],
            generated_solution_assets=generated(case, context),
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


class ReadOnlyAssetMetadata:
    def __init__(self, specs):
        self.specs = specs

    def get_source_asset(self, identifier):
        for spec in self.specs:
            if identifier == "preview-" + spec["sha256"][:16]:
                return {"source_asset": {"sha256": spec["sha256"]}}
        raise AssertionError("unexpected source-asset metadata read")


def generated(case, context=None):
    ctx = case["context"] if context is None else context
    specs = get_handler(GROUPS[case["group"]]["rule"]).diagram_specs(ctx)
    return _generated_diagram_assets(
        ReadOnlyAssetMetadata(specs), ctx, specs, case["task"]
    )
