"""Prepare orthogonal volume methods through the shared frozen content runtime."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import orthogonal_proofs, orthogonal_surface_proofs
from .orthogonal_figures import selection
from .orthogonal_sources import DATA, review_parent


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
    if generated_solution_assets:
        raise ContentPlanError("the exact numerical condition drawings must be reused")
    model = selection(context, content_rule_key)
    if DATA["quantities"][content_rule_key] == "surface":
        return repair_quantity(
            context,
            model.solid.surface,
            orthogonal_surface_proofs.render(
                model, DATA["surface_styles"][content_rule_key]
            ),
        )
    return repair_quantity(
        context,
        model.answer,
        orthogonal_proofs.render(model, DATA["orders"][content_rule_key]),
    )
