"""Prepare reviewed pyramid methods through the shared frozen content runtime."""

from ..quadrilaterals.quantity_repair import repair_quantity
from . import pyramid_figures, pyramid_proofs
from .pyramid_sources import review_parent


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
    m, changes, pictures, keys = pyramid_figures.prepare(
        context, generated_solution_assets, content_rule_key
    )
    return repair_quantity(
        context, m.answer, pyramid_proofs.render(m, pictures), keys, changes
    )
