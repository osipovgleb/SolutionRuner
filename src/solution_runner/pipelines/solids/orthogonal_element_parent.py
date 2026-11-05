"""Prepare named orthogonal elements through the shared frozen quantity runtime."""

from ..quadrilaterals.quantity_repair import repair_quantity
from .orthogonal_element_figures import prepare as figures
from .orthogonal_element_proofs import render
from .orthogonal_element_sources import METHODS, review_parent


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
    model, picture, keys, changes = figures(
        context, METHODS[content_rule_key], generated_solution_assets
    )
    return repair_quantity(context, model.value, render(model, picture), keys, changes)
