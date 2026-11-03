"""Native source examples for the shared isosceles base/side preparation."""

import json
from pathlib import Path

from solution_runner.pipelines.triangles.isosceles.basic_model import read_question

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_isosceles_basic_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}
PARENTS = {c["group"]: c for c in CASES if c["task"] == c["group"]}


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


def parent_html(group):
    return section(PARENTS[group]["context"], "solution")["html"]


def model(case, context=None):
    ctx = case["context"] if context is None else context
    source = next(
        a["asset_id"]
        for a in ctx["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    return read_question(section(ctx, "condition")["html"], source).require_rule(
        GROUPS[case["group"]]["rule"]
    )


class PreviewMetadata:
    def __init__(self, specs):
        self.specs = specs

    def get_source_asset(self, identifier):
        for spec in self.specs:
            if identifier == "preview-" + spec["sha256"][:16]:
                return {"source_asset": {"sha256": spec["sha256"]}}
        raise AssertionError("unexpected metadata read")


def plan(case, context=None, parent=None):
    from solution_runner.pipelines.core.content_runtime import (
        _generated_diagram_assets,
        _solution_assets,
    )
    from solution_runner.pipelines.core.handler_registry import get_handler
    from solution_runner.pipelines.core.handlers import PlanInput

    ctx = case["context"] if context is None else context
    parent_context = PARENTS[case["group"]]["context"]
    source = next(
        a["asset_id"]
        for a in parent_context["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    handler = get_handler(GROUPS[case["group"]]["rule"])
    specs = handler.diagram_specs(ctx)
    generated = _generated_diagram_assets(
        PreviewMetadata(specs), ctx, specs, case["task"]
    )
    return handler.plan(
        PlanInput(
            ctx,
            parent_asset_id=source,
            parent_solution_assets=_solution_assets(parent_context),
            parent_solution_html=parent_html(case["group"])
            if parent is None
            else parent,
            generated_solution_assets=generated,
        )
    )
