"""Declare the cube family once with strict frozen preparation and readback."""

from ..core.handlers import HandlerSpec
from .cube_sources import PARENTS

HANDLERS = tuple(
    HandlerSpec(
        rule,
        "solution_runner.pipelines.solids.cube_parent:prepare",
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
        diagram_builder="solution_runner.pipelines.solids.cube_figures:diagram_specs",
    )
    for rule in PARENTS
)
