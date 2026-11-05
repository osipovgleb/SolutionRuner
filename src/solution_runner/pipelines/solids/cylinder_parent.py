"""Prepare actual cylinder quantities through pinned methods and the shared runtime."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import cylinder_figures, cylinder_proofs
from .cylinder_sources import RULES, review_parent


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
    m, changes, picture, keys = cylinder_figures.prepare(
        context, generated_solution_assets, rule=content_rule_key
    )
    if m.mode != RULES[content_rule_key]:
        raise ContentPlanError(
            "the complete cylinder question differs from its parent method"
        )
    return repair_quantity(
        context, m.answer, cylinder_proofs.render(m, picture), keys, changes
    )
