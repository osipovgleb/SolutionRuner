"""Shared native contexts and public preview preparation for angle families."""

import json
from pathlib import Path

from isosceles_basic_cases import PreviewMetadata

from solution_runner.pipelines.core.content_runtime import _generated_diagram_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_isosceles_angle_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
GROUPS = {g["key"]: g for g in DATA["groups"]}
PARENTS = {c["group"]: c for c in CASES if c["task"] == c["group"]}


def section(context, key):
    return next(s for s in context["normalized_content"]["sections"] if s["key"] == key)


def parent_html(group):
    return section(PARENTS[group]["context"], "solution")["html"]


def plan(case, context=None, parent=None):
    ctx = case["context"] if context is None else context
    handler = get_handler(GROUPS[case["group"]]["rule"])
    specs = handler.diagram_specs(ctx)
    generated = _generated_diagram_assets(
        PreviewMetadata(specs), ctx, specs, case["task"]
    )
    return handler.plan(
        PlanInput(
            ctx,
            parent_asset_id=next(
                a["asset_id"]
                for a in PARENTS[case["group"]]["context"]["normalized_content"][
                    "assets"
                ]
                if a["asset_key"] == "image_1"
            ),
            parent_solution_html=parent_html(case["group"])
            if parent is None
            else parent,
            generated_solution_assets=generated,
        )
    )
