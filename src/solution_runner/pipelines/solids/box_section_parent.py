"""Prepare both section groups through one actual-plane model and parent method."""

from ..quadrilaterals.quantity_repair import repair_quantity
from . import box_section_figures, box_section_proof
from .box_section_sources import review_parent


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
    m, changes, picture, keys = box_section_figures.prepare(
        context, generated_solution_assets, rule=content_rule_key
    )
    return repair_quantity(
        context, m.answer, box_section_proof.render(m, picture), keys, changes
    )
