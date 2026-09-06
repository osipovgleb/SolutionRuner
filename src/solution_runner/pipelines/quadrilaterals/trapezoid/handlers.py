"""Explicit handler declarations; adding a group needs no runtime branch."""
from solution_runner.pipelines.core.handlers import HandlerSpec

HANDLERS = (
    HandlerSpec('trapezoid-77152-isosceles-leg-from-sine', 'solution_runner.pipelines.quadrilaterals.trapezoid.group_77152_planner:build_repair_plan',
        inputs=(('parent_condition_asset_id', 'parent_asset_id'),)),
)
