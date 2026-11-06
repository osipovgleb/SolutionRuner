"""Reviewed midpoint, prism and symmetric-tetrahedron projection scenes."""

RULES = {
    "solid-box-midpoint-line-projection-angle": "box_tetrahedron_line_projection_angle",
    "solid-triangle-pyramid-midpoint-projection-angle": "triangle_pyramid_midpoint_projection_angle",
    "solid-triangle-prism-line-projection-angle": "triangle_prism_line_projection_angle",
    "solid-symmetric-tetrahedron-projection-angle": (
        "symmetric_tetrahedron_line_plane_angle",
        "triangle_pyramid_parallel_rectangle_distance",
    ),
}
ROLES = {
    "triangle_pyramid_midpoint_projection_angle": (
        ("solution", "image_1", "d675c1b8-41ab-4d64-b444-75ab05b87ec1"),
    ),
    "symmetric_tetrahedron_line_plane_angle": (
        ("solution", "image_1", "c7e3fb7d-1da4-4bf1-b096-fd89329cc2c3"),
    ),
    "triangle_pyramid_parallel_rectangle_distance": (
        ("solution", "image_1", "b86e89a7-5294-4ba2-8c9c-792773074ed8"),
    ),
}


def roles(model):
    if model.mode == "box_tetrahedron_line_projection_angle":
        sources = {
            "midpoint_side": "2db630ef-b2b5-4669-a9ac-3eae77d6b1a7",
            "midpoint_base": "2ec2e407-a0db-417f-a69d-9c18bb3c894c",
        }
        if model.names[0] in sources:
            return (("solution", "image_1", sources[model.names[0]]),)
    if model.mode == "triangle_prism_line_projection_angle":
        if model.symbols["base"] == "right":
            return (("solution", "image_1", "f3c2a42f-5ef0-4fe7-a941-b2613124be39"),)
        source = (
            "8a9c6676-fa04-4271-a557-ccf630c55a82"
            if model.symbols["claim"] == "square"
            else "8dac3233-9ae3-430c-831b-d3d74edc87eb"
        )
        return (
            ("solution", "image_1", source),
            ("solution", "image_2", "9f5b6d3e-48ab-40a6-a853-da8f7033aaef"),
        )
    return ROLES.get(model.mode)


GROUPS = (
    (
        "507611",
        "50995c87-cda7-415b-8014-338c4b75600f",
        4,
        "Угол между прямой и плоскостью",
        8,
        "6a0a2bae-d44e-404e-a770-89f4f5517cde",
        "solid-box-midpoint-line-projection-angle",
    ),
    (
        "484559",
        "99c3fda7-ad69-4ee5-b6de-12dd8b20e628",
        5,
        "Угол между прямой и плоскостью",
        8,
        "6a0a2bae-d44e-404e-a770-89f4f5517cde",
        "solid-triangle-pyramid-midpoint-projection-angle",
    ),
    (
        "485934",
        "c19d8820-127d-4ccc-bc2a-f3ee40782f85",
        6,
        "Угол между прямой и плоскостью",
        8,
        "6a0a2bae-d44e-404e-a770-89f4f5517cde",
        "solid-triangle-prism-line-projection-angle",
    ),
    (
        "525393",
        "06585414-b9d8-4d48-88ca-fa49a0341fb7",
        14,
        "Угол между прямой и плоскостью",
        8,
        "6a0a2bae-d44e-404e-a770-89f4f5517cde",
        "solid-symmetric-tetrahedron-projection-angle",
    ),
)
