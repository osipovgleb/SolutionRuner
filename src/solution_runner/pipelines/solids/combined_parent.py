"""Prepare shared solid-combination solutions through the frozen content runtime."""

from ..quadrilaterals.quantity_repair import repair_quantity
from . import combined_figures, combined_proofs
from .combined_sources import DATA, review_parent


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
    m, changes, pictures, keys = combined_figures.prepare(
        context, generated_solution_assets, content_rule_key
    )
    return repair_quantity(
        context,
        m.answer,
        combined_proofs.render(m, pictures, DATA["styles"][content_rule_key]),
        keys,
        changes,
    )
