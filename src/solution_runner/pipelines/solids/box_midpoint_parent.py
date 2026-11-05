"""Prepare the reviewed midpoint method using actual section geometry and exact figures."""

from ..quadrilaterals.quantity_repair import repair_quantity
from . import box_midpoint_figures, box_midpoint_proof
from .box_midpoint_sources import review_parent


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
    content_rule_key,
):
    review_parent(
        content_rule_key,
        parent_condition_asset_id,
        parent_solution_html,
        parent_solution_assets,
    )
    m, changes, picture, keys = box_midpoint_figures.prepare(
        context, generated_solution_assets
    )
    return repair_quantity(
        context, m.answer, box_midpoint_proof.render(m, picture), keys, changes
    )
