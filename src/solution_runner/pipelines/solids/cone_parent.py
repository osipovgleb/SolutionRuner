"""Prepare cone quantities through reviewed parent methods and the shared content runtime."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import cone_figures, cone_proofs
from .cone_sources import RULES, review_parent


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
    m, changes, picture, keys = cone_figures.prepare(
        context, generated_solution_assets, rule=content_rule_key
    )
    mode, kind = RULES[content_rule_key]
    if m.mode != mode or kind is not None and m.kind != kind:
        raise ContentPlanError(
            "the complete cone question differs from its parent method"
        )
    return repair_quantity(
        context, m.answer, cone_proofs.render(m, picture), keys, changes
    )
