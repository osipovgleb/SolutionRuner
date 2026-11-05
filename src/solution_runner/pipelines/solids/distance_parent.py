"""Prepare actual named spatial distances through reviewed parent methods."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import distance_figures, distance_proofs
from .distance_answer_figures import repair_answer
from .distance_sources import RULES, review_parent


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
    model, changes, picture, keys = distance_figures.prepare(
        context, generated_solution_assets
    )
    allowed = RULES[content_rule_key]
    allowed = (allowed,) if isinstance(allowed, str) else allowed
    if model.mode not in allowed:
        raise ContentPlanError(
            "the complete spatial question differs from its parent method"
        )
    html = distance_proofs.render(model, picture)
    if model.mode == "box_diagonal_bisector_ratio":
        from .box_bisector_answer import prepare as ratio_answer

        return ratio_answer(context, model, html, keys, changes)
    return repair_answer(
        repair_quantity(context, model.answer, html, keys, changes),
        context,
    )
