"""Declare solid families once with strict frozen preparation and readback."""

from ..core.handlers import HandlerSpec
from .box_midpoint_sources import PARENTS as MIDPOINTS
from .box_section_sources import PARENTS as SECTIONS
from .box_sources import PARENTS as BOX
from .cube_sources import PARENTS as CUBE
from .cylinder_sources import PARENTS as CYLINDERS
from .distance_sources import PARENTS as DISTANCES
from .line_angle_sources import PARENTS as LINE_ANGLES
from .polyhedron_sources import PARENTS as POLYHEDRA
from .sphere_sources import PARENTS as SPHERES
from .vertex_angle_sources import PARENTS as VERTEX_ANGLES

HANDLERS = tuple(
    HandlerSpec(
        rule,
        target,
        inputs=(
            ("parent_condition_asset_id", "parent_asset_id"),
            ("parent_solution_html", "parent_solution_html"),
            ("parent_solution_assets", "parent_solution_assets"),
            ("generated_solution_assets", "generated_solution_assets"),
        ),
        options=(("content_rule_key", rule),),
        parent_from_group_listing=True,
        requires_parent_condition_asset=parents[rule][0] is not None,
        requires_frozen_manifest=True,
        verify_content_readback=True,
        strict_frozen_input=True,
        diagram_builder=builder[rule] if isinstance(builder, dict) else builder,
    )
    for parents, target, builder in (
        (
            CUBE,
            "solution_runner.pipelines.solids.cube_parent:prepare",
            "solution_runner.pipelines.solids.cube_figures:diagram_specs",
        ),
        (
            LINE_ANGLES,
            "solution_runner.pipelines.solids.line_angle_parent:prepare",
            "solution_runner.pipelines.solids.line_angle_parent:diagram_specs",
        ),
        (
            VERTEX_ANGLES,
            "solution_runner.pipelines.solids.vertex_angle_parent:prepare",
            {
                "solid-box-angle-from-face-diagonal": "solution_runner.pipelines.solids.vertex_angle_figures:solution_specs",
                "solid-box-angle-from-base-diagonal": "solution_runner.pipelines.solids.vertex_angle_figures:condition_specs",
            },
        ),
        (
            POLYHEDRA,
            "solution_runner.pipelines.solids.polyhedron_parent:prepare",
            {
                "solid-polyhedron-central-tetrahedron": "solution_runner.pipelines.solids.polyhedron_figures:central_specs",
                "solid-polyhedron-half-box": "solution_runner.pipelines.solids.polyhedron_figures:prism_specs",
                "solid-polyhedron-pyramid-with-note": "solution_runner.pipelines.solids.polyhedron_figures:note_specs",
                "solid-polyhedron-triangle-pyramid": "solution_runner.pipelines.solids.polyhedron_figures:triangle_specs",
                "solid-polyhedron-face-pyramid": "solution_runner.pipelines.solids.polyhedron_figures:face_specs",
            },
        ),
        (
            SECTIONS,
            "solution_runner.pipelines.solids.box_section_parent:prepare",
            {
                "solid-box-vertical-section": "solution_runner.pipelines.solids.box_section_figures:vertical_specs",
                "solid-box-oblique-section": "solution_runner.pipelines.solids.box_section_figures:oblique_specs",
            },
        ),
        (
            MIDPOINTS,
            "solution_runner.pipelines.solids.box_midpoint_parent:prepare",
            "solution_runner.pipelines.solids.box_midpoint_figures:diagram_specs",
        ),
        (BOX, "solution_runner.pipelines.solids.box_parent:prepare", None),
        (SPHERES, "solution_runner.pipelines.solids.sphere_parent:prepare", None),
        (CYLINDERS, "solution_runner.pipelines.solids.cylinder_parent:prepare", None),
        (
            DISTANCES,
            "solution_runner.pipelines.solids.distance_parent:prepare",
            "solution_runner.pipelines.solids.distance_figures:diagram_specs",
        ),
    )
    for rule in parents
)
