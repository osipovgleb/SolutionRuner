"""Explicit handler declarations; adding a group needs no runtime branch."""

from solution_runner.pipelines.core.handlers import HandlerSpec

from .isosceles_model import RULES

HANDLERS = (
    HandlerSpec(
        "trapezoid-77152-isosceles-leg-from-sine",
        "solution_runner.pipelines.quadrilaterals.trapezoid.group_77152_planner:build_repair_plan",
        inputs=(("parent_condition_asset_id", "parent_asset_id"),),
    ),
)


HANDLERS += tuple(
    HandlerSpec(
        rule,
        "solution_runner.pipelines.quadrilaterals.trapezoid.isosceles_parent:prepare",
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", rule),),
        parent_from_group_listing=True,
        requires_frozen_manifest=True,
        verify_content_readback=True,
        strict_frozen_input=True,
        diagram_builder="solution_runner.pipelines.quadrilaterals.trapezoid.isosceles_figures:diagram_specs",
    )
    for rule in RULES
)
