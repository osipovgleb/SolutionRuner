"""One reviewed cube preparer, without task IDs or transport side effects."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import cube_figures, cube_proofs
from .cube_sources import RULES, review_parent


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
    model = cube_figures.model(context)
    if RULES[content_rule_key] != model.mode:
        raise ContentPlanError(
            "the complete cube question differs from its parent method"
        )
    changes, pictures, keys = cube_figures.prepare(
        context, model, generated_solution_assets, parent_condition_asset_id
    )
    return repair_quantity(
        context, model.answer, cube_proofs.render(model, pictures), keys, changes
    )
