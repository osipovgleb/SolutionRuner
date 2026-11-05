"""Declare solid families once with strict frozen preparation and readback."""

from ..core.handlers import HandlerSpec
from .box_sources import PARENTS as BOX
from .cube_sources import PARENTS as CUBE

HANDLERS = tuple(
    HandlerSpec(
        rule,
        target,
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
        diagram_builder=builder,
    )
    for parents, target, builder in (
        (
            CUBE,
            "solution_runner.pipelines.solids.cube_parent:prepare",
            "solution_runner.pipelines.solids.cube_figures:diagram_specs",
        ),
        (BOX, "solution_runner.pipelines.solids.box_parent:prepare", None),
    )
    for rule in parents
)
