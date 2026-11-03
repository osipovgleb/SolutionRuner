"""Explicit midpoint-area methods share one validated mathematical preparer."""

from solution_runner.pipelines.core.handlers import HandlerSpec

from .midpoint_model import HEIGHT, TWO_TRAPEZOID, TWO_TRIANGLE, VARIGNON

HANDLERS = tuple(
    HandlerSpec(
        rule,
        "solution_runner.pipelines.quadrilaterals.parallelogram.midpoint_parent:prepare",
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
        diagram_builder="solution_runner.pipelines.quadrilaterals.parallelogram.midpoint_figures:diagram_specs",
    )
    for rule in (HEIGHT, TWO_TRAPEZOID, TWO_TRIANGLE, VARIGNON)
)
