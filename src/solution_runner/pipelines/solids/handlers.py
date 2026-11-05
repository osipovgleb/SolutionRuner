"""Declare solid families once with strict frozen preparation and readback."""

from ..core.handlers import HandlerSpec
from .box_sources import PARENTS as BOX
from .cube_sources import PARENTS as CUBE
from .distance_sources import PARENTS as DISTANCES
from .line_angle_sources import PARENTS as LINE_ANGLES
from .vertex_angle_sources import PARENTS as VERTEX_ANGLES

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
        diagram_builder=builder[rule] if isinstance(builder, dict) else builder,
    )
    for parents, target, builder in (
        (
            CUBE,
            "solution_runner.pipelines.solids.cube_parent:prepare",
            "solution_runner.pipelines.solids.cube_figures:diagram_specs",
        ),
        (
            LINE_ANGLES,
            "solution_runner.pipelines.solids.line_angle_parent:prepare",
            "solution_runner.pipelines.solids.line_angle_parent:diagram_specs",
        ),
        (
            VERTEX_ANGLES,
            "solution_runner.pipelines.solids.vertex_angle_parent:prepare",
            {
                "solid-box-angle-from-face-diagonal": "solution_runner.pipelines.solids.vertex_angle_figures:solution_specs",
                "solid-box-angle-from-base-diagonal": "solution_runner.pipelines.solids.vertex_angle_figures:condition_specs",
            },
        ),
        (BOX, "solution_runner.pipelines.solids.box_parent:prepare", None),
        (
            DISTANCES,
            "solution_runner.pipelines.solids.distance_parent:prepare",
            "solution_runner.pipelines.solids.distance_figures:diagram_specs",
        ),
    )
    for rule in parents
)
