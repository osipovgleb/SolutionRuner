"""Prepare acute box angles only after proving equal perpendicular legs."""

from ..quadrilaterals.quantity_repair import repair_quantity
from . import vertex_angle_figures, vertex_angle_proof
from .vertex_angle_sources import review_parent


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
    m, changes, picture, keys = vertex_angle_figures.prepare(
        context,
        generated_solution_assets,
        with_solution=vertex_angle_figures.RULES[content_rule_key],
    )
    return repair_quantity(
        context, m.answer, vertex_angle_proof.render(m, picture), keys, changes
    )
