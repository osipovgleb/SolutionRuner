"""One parent-pinned preparer for exact circle angles and chord quantities."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import (
    angle_figures,
    angle_model,
    angle_proofs,
    incircle_figures,
    incircle_model,
    incircle_proofs,
    tangent_figures,
    tangent_model,
    tangent_proofs,
)
from .quantity_sources import review_parent

FAMILIES = {
    **dict.fromkeys(
        angle_model.RULES,
        (angle_model.RULES, angle_figures.prepare, angle_proofs.render),
    ),
    **dict.fromkeys(
        tangent_model.RULES,
        (tangent_model.RULES, tangent_figures.prepare, tangent_proofs.render),
    ),
    **dict.fromkeys(
        incircle_model.RULES,
        (incircle_model.RULES, incircle_figures.prepare, incircle_proofs.render),
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
        raise ContentPlanError(
            "an explicit reviewed circle-quantity family is required"
        )
    rules, prepare_figures, render = FAMILIES[content_rule_key]
    review_parent(
        content_rule_key,
        parent_condition_asset_id,
        parent_solution_html,
        parent_solution_assets,
    )
    model, changes, pictures, keys = prepare_figures(context, generated_solution_assets)
    if rules[content_rule_key] != model.mode:
        raise ContentPlanError(
            "the complete circle question differs from its parent method"
        )
    return repair_quantity(
        context, model.answer, render(model, pictures), keys, changes
    )
