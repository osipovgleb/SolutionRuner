"""Select the reviewed parent's geometric method and retain solution drawings."""

from . import combined_cube_proofs as cube
from . import combined_prism_proofs as prism
from . import combined_ratio_proofs as ratio

RENDERERS = {
    "sphere_cylinder_surface": ratio.sphere_cylinder_surface,
    "cylinder_sphere_surface": ratio.sphere_cylinder_surface,
    "sphere_cylinder_volume": ratio.sphere_cylinder_volume,
    "cylinder_sphere_volume": ratio.sphere_cylinder_volume,
    "cone_sphere_volume": ratio.cone_sphere,
    "sphere_cone_volume": ratio.cone_sphere,
    "cone_cylinder_lateral": ratio.cone_cylinder_lateral,
    "pyramid_cones_ratio": ratio.pyramid_cones,
    "pyramid_outer_cone_volume": ratio.pyramid_cones,
    "pyramid_inner_cone_volume": ratio.pyramid_cones,
    "tetra_midpoint_volume": ratio.tetra_midpoints,
    "tetra_midpoint_surface": ratio.tetra_midpoints,
    "cube_around_sphere_volume": cube.cube_around,
    "cube_around_sphere_surface": cube.cube_around,
    "cube_insphere_radius": cube.insphere_radius,
    "cube_insphere_volume": cube.sphere_volume,
    "cube_circumsphere_volume": cube.sphere_volume,
    "cube_in_sphere_volume": cube.cube_in_sphere,
    "cube_sphere_volume": cube.cube_from_ball_volume,
    "sphere_vertex_part": cube.sphere_part,
    "sphere_edge_part": cube.sphere_part,
    "cube_prism_hole": cube.cube_hole,
    "box_cylinder_volume": prism.box,
    "box_cylinder_height": prism.box,
    "cylinder_around_triangle": prism.cylinder_around,
    "cylinder_around_square": prism.cylinder_around,
    "square_cylinder_lateral": prism.regular_prism,
    "square_cylinder_height": prism.regular_prism,
    "triangle_around_cylinder_lateral": prism.regular_prism,
    "triangle_in_cylinder_lateral": prism.regular_prism,
    "hexagon_cylinder_lateral": prism.regular_prism,
    "pyramid_cone_volume": prism.pyramid_cone,
    "cone_sphere_radius": prism.cone_sphere,
    "cone_sphere_slant": prism.cone_sphere,
}


def render(m, pictures, style):
    prefix = "".join("<p>" + picture + "</p>" for picture in pictures.values())
    if m.kind in {"cylinder_cone_volume", "cone_cylinder_volume"}:
        return prefix + ratio.cone_cylinder(m, cylinder_first=style == "cylinder_first")
    return prefix + RENDERERS[m.kind](m)
