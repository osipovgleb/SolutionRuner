"""Reviewed triangle, prism and tetrahedron illustrations retain their proof roles."""

RULES = {
    "solid-hexagonal-pyramid-skew-angle": "hexagonal_pyramid_skew_angle",
    "solid-triangle-prism-midpoint-pentahedron-volume": "triangle_prism_midpoint_pentahedron_volume",
    "solid-perpendicular-equilateral-triangle-volume": "perpendicular_equilateral_triangle_volume",
    "solid-tetra-midpoint-cut-volume-ratio": "tetra_midpoint_cut_volume_ratio",
}
ROLES = {
    "hexagonal_pyramid_skew_angle": (
        ("solution", "image_1", "9f3ee955-ce64-4202-abd1-669a222624ec"),
    ),
    "triangle_prism_midpoint_pentahedron_volume": (
        ("solution", "image_1", "0af8f9a4-e6be-4ed3-adc4-f1a9dbd92a24"),
    ),
    "perpendicular_equilateral_triangle_volume": (
        ("solution", "image_1", "817d8b59-ebad-456e-b4f3-8061474d9f8f"),
    ),
    "tetra_midpoint_cut_volume_ratio": (
        ("solution", "image_1", "7745066b-496f-43d1-bad0-f0de3a76f409"),
    ),
}


def roles(model):
    if model.mode == "hexagonal_pyramid_skew_angle":
        source = {
            "angle_equal": "9f3ee955-ce64-4202-abd1-669a222624ec",
            "SBD": "ba6ca144-098c-4e06-a039-dc8492a2fabd",
            "SBC": "7370c560-ab1f-477f-8c75-5aecb3d262ee",
        }[model.names[2]]
        return (("solution", "image_1", source),)
    if (
        model.mode == "triangle_prism_midpoint_pentahedron_volume"
        and model.names[0] == "upper"
    ):
        return (("solution", "image_1", "31aa2d97-1538-43bb-9118-c1405eff780a"),)
    if (
        model.mode == "perpendicular_equilateral_triangle_volume"
        and model.names[0] == "C"
    ):
        source = (
            "66698c94-9d6c-4e6e-b08b-325f23836809"
            if model.names[2] == "inequality"
            else "9ebdffb1-4af5-474e-a317-64db6cd383c6"
        )
        return (("solution", "image_1", source),)
    return ROLES.get(model.mode)


GROUPS = (
    (
        "484567",
        "ee86113d-8b6e-45cd-b1b1-ffb983cdea29",
        9,
        "Угол между скрещивающимися прямыми",
        9,
        "040a2eaa-4afa-4fb3-b24a-f8ef0b03a038",
        "solid-hexagonal-pyramid-skew-angle",
    ),
    (
        "501436",
        "a9a94bd2-9608-4165-9d4d-dcf29e77cfd7",
        0,
        "Объёмы многогранников",
        10,
        "83d8387d-477a-481b-ae56-d90bddb01e4b",
        "solid-triangle-prism-midpoint-pentahedron-volume",
    ),
    (
        "501549",
        "9ea5fcb3-e4c2-4deb-aa69-1a4a347dfd68",
        1,
        "Объёмы многогранников",
        10,
        "83d8387d-477a-481b-ae56-d90bddb01e4b",
        "solid-perpendicular-equilateral-triangle-volume",
    ),
    (
        "517446",
        "2ca45e7f-c6a5-439d-a84b-ccd428de5826",
        8,
        "Объёмы многогранников",
        10,
        "83d8387d-477a-481b-ae56-d90bddb01e4b",
        "solid-tetra-midpoint-cut-volume-ratio",
    ),
)
