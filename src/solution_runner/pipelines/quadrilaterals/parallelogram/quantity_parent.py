"""Prepare the reviewed height and rhombus methods without transport side effects."""

from ...core.errors import ContentPlanError
from ..quantity_repair import repair_quantity
from .quantity_figures import prepare as prepare_figures
from .quantity_model import RULES
from .quantity_proofs import render
from .quantity_sources import review_parent


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
    model, changes, pictures, keys = prepare_figures(context, generated_solution_assets)
    mode = "side_difference" if model.mode == "side_known" else model.mode
    if RULES[content_rule_key] != mode:
        raise ContentPlanError(
            "the complete quantity question differs from its parent method"
        )
    return repair_quantity(
        context, model.answer, render(model, pictures), keys, changes
    )
