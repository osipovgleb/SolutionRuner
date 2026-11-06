"""Reviewed proof roles distinguish midpoint positions and numeric triangle lengths."""

RULES = {
    "solid-triangle-prism-split-edge-projection-angle": "triangle_prism_split_edge_projection_angle",
    "solid-tetrahedron-midpoint-diagonal-angle": "tetra_parallel_midpoint_diagonal_angle",
    "solid-cube-midpoint-skew-angle": "cube_midpoint_skew_angle",
    "solid-triangle-pyramid-midpoint-skew-cosine": "triangle_pyramid_midpoint_skew_cosine",
}
ROLES = {
    "triangle_prism_split_edge_projection_angle": (
        ("solution", "image_1", "5e775e0f-9a27-448c-8dbb-414e9ed8f975"),
        ("solution", "image_2", "5c2d3b08-3c01-4a5f-8b17-fa6d6f7d49d3"),
        ("solution", "image_3", "f36861d0-d5a9-4fc0-b15c-db19025a3c83"),
    ),
    "tetra_parallel_midpoint_diagonal_angle": (
        ("solution", "image_1", "5188f420-5196-4fd0-90a9-0feab8ef7974"),
    ),
    "cube_midpoint_skew_angle": (
        ("solution", "image_1", "f1cc9df4-eadc-44a8-80b3-b54035b53483"),
    ),
    "triangle_pyramid_midpoint_skew_cosine": (
        ("solution", "image_1", "7e74e022-072d-4711-95c1-f9d15e7c4895"),
        ("solution", "image_2", "c1c985d9-dbdd-4108-a141-df0d57d1fe84"),
    ),
}


def roles(model):
    if (
        model.mode == "tetra_parallel_midpoint_diagonal_angle"
        and model.names[0] == "DA"
    ):
        return (("solution", "image_1", "ae16ebb9-f91b-4565-a024-4f3ef002d281"),)
    if model.mode == "cube_midpoint_skew_angle" and model.names[0] == "space":
        source = (
            "da0f375f-deed-4d19-a4e1-2141d524aa05"
            if model.names[1] == "A"
            else "0b7a06f4-6a05-41eb-b279-bdcb58151af9"
        )
        return (("solution", "image_1", source),)
    return ROLES.get(model.mode)


GROUPS = (
    (
        "699395",
        "2fbe9559-bde9-41ad-a79b-e8c07106de8d",
        27,
        "Угол между прямой и плоскостью",
        8,
        "6a0a2bae-d44e-404e-a770-89f4f5517cde",
        "solid-triangle-prism-split-edge-projection-angle",
    ),
    (
        "509423",
        "4416c079-a9ff-4261-bcc9-9f14a8745a84",
        4,
        "Угол между скрещивающимися прямыми",
        9,
        "040a2eaa-4afa-4fb3-b24a-f8ef0b03a038",
        "solid-tetrahedron-midpoint-diagonal-angle",
    ),
    (
        "500112",
        "0851d227-5632-47e4-b207-043859e78cd5",
        5,
        "Угол между скрещивающимися прямыми",
        9,
        "040a2eaa-4afa-4fb3-b24a-f8ef0b03a038",
        "solid-cube-midpoint-skew-angle",
    ),
    (
        "505387",
        "08d62da0-21f1-42dc-a1be-b81ab34b1c47",
        7,
        "Угол между скрещивающимися прямыми",
        9,
        "040a2eaa-4afa-4fb3-b24a-f8ef0b03a038",
        "solid-triangle-pyramid-midpoint-skew-cosine",
    ),
)
