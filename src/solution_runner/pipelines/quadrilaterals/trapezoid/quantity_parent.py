"""One parent-pinned quantity preparer for the exact trapezoid families."""

from ...core.errors import ContentPlanError
from ..quantity_repair import repair_quantity
from . import (
    altitude_figures,
    altitude_model,
    altitude_proofs,
    isosceles_figures,
    isosceles_model,
    isosceles_proofs,
)
from .quantity_sources import review_parent

FAMILIES = {
    **dict.fromkeys(
        isosceles_model.RULES,
        (isosceles_model.RULES, isosceles_figures.prepare, isosceles_proofs.render),
    ),
    **dict.fromkeys(
        altitude_model.RULES,
        (altitude_model.RULES, altitude_figures.prepare, altitude_proofs.render),
    ),
}


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
    content_rule_key,
):
    if content_rule_key not in FAMILIES:
        raise ContentPlanError("an explicit trapezoid family is required")
    rules, prepare_figures, render = FAMILIES[content_rule_key]
    review_parent(
        content_rule_key,
        parent_condition_asset_id,
        parent_solution_html,
        parent_solution_assets,
    )
    model, changes, pictures, keys = prepare_figures(
        context, content_rule_key, generated_solution_assets
    )
    if rules[content_rule_key] != model.mode:
        raise ContentPlanError(
            "the complete trapezoid question differs from its parent rule"
        )
    return repair_quantity(
        context, model.answer, render(model, pictures), keys, changes
    )
