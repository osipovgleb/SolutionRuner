"""Native midpoint-perimeter sources use the existing pure planning helpers."""

import json
from pathlib import Path

from midpoint_source_cases import section

from solution_runner.pipelines.core.content_runtime import _solution_assets
from solution_runner.pipelines.core.handler_registry import get_handler
from solution_runner.pipelines.core.handlers import PlanInput
from solution_runner.pipelines.quadrilaterals.parallelogram.midpoint_model import (
    PERIMETER,
)
from solution_runner.pipelines.quadrilaterals.parallelogram.midpoint_sources import (
    PERIMETER_CONDITION,
)

DATA = json.loads(
    (
        Path(__file__).parent / "fixtures/category_1_midpoint_perimeter_sources.json"
    ).read_text()
)
CASES = DATA["cases"]
PARENT = CASES[0]["context"]
ARGUMENTS = {
    "parent_asset_id": PERIMETER_CONDITION,
    "parent_solution_html": section(PARENT, "solution")["html"],
    "parent_solution_assets": _solution_assets(PARENT),
}


def plan(context, **overrides):
    return get_handler(PERIMETER).plan(PlanInput(context, **{**ARGUMENTS, **overrides}))
