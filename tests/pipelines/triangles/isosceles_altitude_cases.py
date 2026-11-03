"""Native side-altitude examples and their complete-condition reader."""

import json
from pathlib import Path

from solution_runner.pipelines.triangles.isosceles.side_altitude_model import (
    read_question,
)

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_isosceles_altitude_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}
PARENTS = {c["group"]: c for c in CASES if c["task"] == c["group"]}


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


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


def parent_html(group):
    return section(PARENTS[group]["context"], "solution")["html"]


def plan(case, context=None, parent=None):
    from isosceles_basic_cases import PreviewMetadata

    from solution_runner.pipelines.core.content_runtime import (
        _generated_diagram_assets,
        _solution_assets,
    )
    from solution_runner.pipelines.core.handler_registry import get_handler
    from solution_runner.pipelines.core.handlers import PlanInput

    ctx = case["context"] if context is None else context
    original = PARENTS[case["group"]]["context"]
    source = next(
        a["asset_id"]
        for a in original["normalized_content"]["assets"]
        if a["asset_key"] == "image_1"
    )
    handler = get_handler(GROUPS[case["group"]]["rule"])
    specs = handler.diagram_specs(ctx)
    assets = _generated_diagram_assets(PreviewMetadata(specs), ctx, specs, case["task"])
    return handler.plan(
        PlanInput(
            ctx,
            parent_asset_id=source,
            parent_solution_html=parent_html(case["group"])
            if parent is None
            else parent,
            parent_solution_assets=_solution_assets(original),
            generated_solution_assets=assets,
        )
    )
