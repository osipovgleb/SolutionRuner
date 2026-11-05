"""Prepare sphere methods through a shared model, source review and frozen runtime."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import sphere_figures, sphere_proofs
from .sphere_sources import RULES, review_parent


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
    m, mode, changes = sphere_figures.prepare(context, generated_solution_assets)
    if mode != RULES[content_rule_key]:
        raise ContentPlanError("the sphere question differs from its parent's method")
    return repair_quantity(context, m.answer, sphere_proofs.render(m), (), changes)
