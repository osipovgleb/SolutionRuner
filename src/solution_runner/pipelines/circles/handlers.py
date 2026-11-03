"""One handler declaration for the reviewed circle-angle methods."""

from ..core.handlers import HandlerSpec
from .angle_model import RULES as ANGLE_RULES
from .tangent_model import RULES as TANGENT_RULES

HANDLERS = tuple(
    HandlerSpec(
        rule,
        "solution_runner.pipelines.circles.quantity_parent:prepare",
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
    for rules, builder in (
        (ANGLE_RULES, "solution_runner.pipelines.circles.angle_figures:diagram_specs"),
        (
            TANGENT_RULES,
            "solution_runner.pipelines.circles.tangent_figures:diagram_specs",
        ),
    )
    for rule in rules
)
