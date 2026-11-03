"""Prepare the parent's circle-angle method with exact inputs and reviewed assets."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from .angle_figures import prepare as prepare_figures
from .angle_model import RULES
from .angle_proofs import render
from .angle_sources import review_parent


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
    if RULES[content_rule_key] != model.mode:
        raise ContentPlanError(
            "the complete circle-angle question differs from its parent method"
        )
    return repair_quantity(
        context, model.answer, render(model, pictures), keys, changes
    )
