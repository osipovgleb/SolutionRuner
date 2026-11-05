"""Complete source contexts and shared preview bindings for the final solid groups."""

import json
from pathlib import Path

from bs4 import BeautifulSoup
from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import (
    _condition_asset_id,
    _solution_assets,
)
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.solids.cylinder_figures import selection as cylinder
from solution_runner.pipelines.solids.polyhedron_figures import selection as polyhedron

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_3_remaining_solids_sources.json"
    ).read_text()
)
GROUPS = {g["key"]: g for g in DATA["groups"]}
CASES = DATA["cases"]
BOUND = [c for c in CASES if "unsupported_reason" not in c]
PENDING = [c for c in CASES if "unsupported_reason" in c]


def arguments(group):
    ctx = next(c["context"] for c in CASES if c["task"] == group)
    return {
        "parent_asset_id": _condition_asset_id(ctx),
        "parent_solution_html": section(ctx, "solution")["html"],
        "parent_solution_assets": _solution_assets(ctx),
    }


def plan(case, context=None, **overrides):
    ctx = case["context"] if context is None else context
    handler = get_handler(GROUPS[case["group"]]["rule"])
    generated = tuple(
        {
            "asset_key": s["asset_key"],
            "sha256": s["sha256"],
            "source_asset_id": "preview-" + s["sha256"][:16],
            "url": "/assets/preview-" + s["sha256"][:16],
        }
        for s in handler.diagram_specs(ctx)
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


def read(case, context=None):
    return (cylinder if case["group"] == "27091" else polyhedron)(
        case["context"] if context is None else context,
        rule=GROUPS[case["group"]]["rule"],
    )[0]


def expected(case):
    soup = BeautifulSoup(section(case["context"], "answer")["html"], "html.parser")
    n = soup.select_one("[data-inline-latex]")
    return n["data-inline-latex"] if n else soup.get_text(strip=True)
