"""Select the parent's geometric method while keeping each source drawing in its role."""

from . import pyramid_basic_proofs as basic
from . import pyramid_ratio_proofs as ratios
from . import pyramid_regular_proofs as regular

BASE = {
    "rectangle_volume",
    "rectangle_height",
    "triangle_volume",
    "triangle_height",
    "center_volume",
    "center_height",
    "center_area",
}
RATIOS = {
    "scale_height",
    "scale_volume",
    "scale_area",
    "hex_whole",
    "square_midpoint",
    "midline_cut",
    "edge_cut",
    "box_tetrahedron",
    "cube_center",
    "tetra_section",
    "square_section",
}


def render(m, pictures):
    prefix = "".join("<p>" + p + "</p>" for p in pictures.values())
    if m.kind in BASE:
        return prefix + basic.base(m)
    if m.kind == "floor":
        return prefix + basic.floor(m)
    if m.kind in {"triangle_lateral", "triangle_side", "triangle_apothem"}:
        return prefix + basic.triangular_lateral(m)
    if m.kind in RATIOS:
        return prefix + ratios.render(m)
    apothem = (
        "h"
        if m.kind in {"square_total_edge", "square_total_height", "hex_lateral_edge"}
        or m.kind == "square_lateral_height"
        and pictures
        else "l"
    )
    return prefix + regular.render(m, apothem)
