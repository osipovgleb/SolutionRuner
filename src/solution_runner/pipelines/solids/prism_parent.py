"""Prepare reviewed prism quantities using the shared frozen content runtime."""

from ..quadrilaterals.quantity_repair import repair_quantity
from . import prism_figures, prism_proofs
from .prism_sources import review_parent


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
    m, changes, pictures, keys = prism_figures.prepare(
        context, generated_solution_assets, rule=content_rule_key
    )
    return repair_quantity(
        context, m.answer, prism_proofs.render(m, pictures), keys, changes
    )
