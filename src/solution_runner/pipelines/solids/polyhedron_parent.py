"""Prepare actual polyhedron volumes through pinned parent methods and shared figures."""

from ..quadrilaterals.quantity_repair import repair_quantity
from . import polyhedron_figures, polyhedron_proofs
from .polyhedron_sources import STYLES, review_parent


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
    m, changes, picture, keys = polyhedron_figures.prepare(
        context, generated_solution_assets, rule=content_rule_key
    )
    return repair_quantity(
        context,
        m.answer,
        polyhedron_proofs.render(
            m,
            picture,
            note=STYLES[content_rule_key]["note"],
            relative=STYLES[content_rule_key].get("relative", False),
        ),
        keys,
        changes,
    )
