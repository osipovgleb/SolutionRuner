"""Prepare the reviewed isosceles-trapezoid family through shared quantity repair."""

from ...core.errors import ContentPlanError
from ..quantity_repair import repair_quantity
from .isosceles_figures import prepare as prepare_figures
from .isosceles_model import RULES
from .isosceles_proofs import render
from .isosceles_sources import review_parent


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
    model, changes, pictures, keys = prepare_figures(
        context, content_rule_key, generated_solution_assets
    )
    if RULES[content_rule_key] != model.mode:
        raise ContentPlanError(
            "the complete trapezoid question differs from its parent rule"
        )
    return repair_quantity(
        context, model.answer, render(model, pictures), keys, changes
    )
