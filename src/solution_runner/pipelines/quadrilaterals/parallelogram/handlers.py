"""Explicit handler declarations; adding a group needs no runtime branch."""
from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec('parallelogram-665285-midpoint-trapezoid-area', 'solution_runner.pipelines.quadrilaterals.parallelogram.group_665285_planner:build_repair_plan',
        inputs=(('parent_condition_asset_id', 'parent_asset_id'),)),
)
