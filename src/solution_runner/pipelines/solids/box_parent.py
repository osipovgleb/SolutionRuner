"""Prepare reviewed box methods without task IDs or transport side effects."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import box_figures, box_proofs, box_square_face_figures
from .box_sources import RULES, review_parent


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
    picture, keys = "", ()
    if RULES[content_rule_key] == "square_face_volume":
        model, changes, picture, keys = box_square_face_figures.prepare(
            context, generated_solution_assets
        )
    else:
        model, condition, current = box_figures.selection(context)
        changes = box_figures.prepare(
            context,
            condition,
            current,
            parent_condition_asset_id,
            generated_solution_assets,
        )
    if model.mode != RULES[content_rule_key]:
        raise ContentPlanError(
            "the complete box question differs from its parent method"
        )
    return repair_quantity(
        context, model.answer, box_proofs.render(model, picture), keys, changes
    )
