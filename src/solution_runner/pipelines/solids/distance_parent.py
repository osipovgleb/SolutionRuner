"""Prepare actual named spatial distances through reviewed parent methods."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_repair import repair_quantity
from . import distance_figures, distance_proofs, spatial_distance_sources
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
        context,
        generated_solution_assets,
        preferred_sources=spatial_distance_sources.preferred_parent_sources(
            parent_solution_assets
        ),
    )
    allowed = RULES[content_rule_key]
    allowed = (allowed,) if isinstance(allowed, str) else allowed
    if model.mode not in allowed:
        raise ContentPlanError(
            "the complete spatial question differs from its parent method"
        )
    html = distance_proofs.render(model, picture)
    degree_projection = (
        model.mode == "rectangular_pyramid_angle"
        and model.symbols.get("scene_family") == "proved_vertex_projection"
    )
    if (
        degree_projection
        or model.mode
        in {
            "box_skew_distance_normal_angle",
            "rectangular_pyramid_proved_altitude_angle",
            "triangle_prism_line_projection_angle",
            "triangle_pyramid_midpoint_projection_angle",
            "symmetric_tetrahedron_line_plane_angle",
        }
        or (
            model.mode == "box_tetrahedron_line_projection_angle"
            and model.names[0].startswith("midpoint_")
            and model.names[2] == "angle"
        )
    ):
        from .box_bisector_answer import plane_degrees

        return plane_degrees(
            context, model, html, keys, changes, radians=not degree_projection
        )
    if model.mode == "box_diagonal_bisector_ratio":
        from .box_bisector_answer import prepare as ratio_answer

        return ratio_answer(context, model, html, keys, changes)
    if model.mode == "box_transverse_ratio_angle":
        from .box_bisector_answer import transverse

        return transverse(context, model, html, keys, changes)
    return repair_answer(
        repair_quantity(context, model.answer, html, keys, changes),
        context,
    )
