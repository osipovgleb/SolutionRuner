"""Reviewed bindings and scenes for equal cuts and perpendicular-plane proofs."""

from dataclasses import replace

RULES = {
    "solid-tetrahedron-equal-edge-cut-cosine": "tetra_equal_edge_cut_cosine",
    "solid-cube-projection-plane-angle": "cube_projection_plane_angle",
    "solid-box-parallel-diagonal-plane-angle": "box_parallel_plane_angle",
    "solid-rhombus-prism-section-angle": "rhombus_prism_section_angle",
}
ROLES = {
    "tetra_equal_edge_cut_cosine": (
        ("solution", "image_1", "ea37eb93-cf21-4b63-9374-e907de5d3008"),
    ),
    "cube_projection_plane_angle": (
        ("solution", "image_1", "fa49d714-1044-4ae1-93eb-62fa58062e89"),
    ),
    "box_parallel_plane_angle": (
        ("solution", "image_1", "e32531aa-e8dd-49b3-8153-d4d7d5e3fb94"),
    ),
    "rhombus_prism_section_angle": (
        ("solution", "image_1", "647d6cee-deab-4198-9878-a4cec16d6168"),
    ),
}
GROUPS = (
    (
        "701579",
        "aa84f86e-60dd-4205-a96b-79b29a4aad60",
        55,
        "Угол между плоскостями",
        6,
        "d3f765c9-c466-41b2-b237-91d0bea9101b",
        "solid-tetrahedron-equal-edge-cut-cosine",
    ),
    (
        "484562",
        "30206b10-d1e2-4349-b077-346957b4eed6",
        0,
        "Угол между плоскостями граней многогранника",
        7,
        "491f66c5-a69f-4a6c-a153-ae62d9f76d06",
        "solid-cube-projection-plane-angle",
    ),
    (
        "507581",
        "8da4b7b0-4054-4d4b-82a0-ddaf02d0972b",
        4,
        "Угол между плоскостями граней многогранника",
        7,
        "491f66c5-a69f-4a6c-a153-ae62d9f76d06",
        "solid-box-parallel-diagonal-plane-angle",
    ),
    (
        "507695",
        "1f7e682d-24ab-457a-8b73-f99eeed58936",
        9,
        "Угол между плоскостями граней многогранника",
        7,
        "491f66c5-a69f-4a6c-a153-ae62d9f76d06",
        "solid-rhombus-prism-section-angle",
    ),
)


def reviewed_model(model, assets):
    if model.mode == "cube_projection_plane_angle":
        return replace(
            model, symbols={"second_figure": "yes" if "image_2" in assets else "no"}
        )
    return None


def roles(model):
    if model.mode == "cube_projection_plane_angle":
        main = (
            ROLES[model.mode]
            if model.names[0] == "center"
            else (("solution", "image_1", "9ad7a873-18c2-4d1d-b14f-eb06248bbfdc"),)
        )
        return main + (
            (("solution", "image_2", "d04720de-9c0f-481c-94b0-ae0268e592d6"),)
            if model.names[0] == "altitudes"
            and model.symbols.get("second_figure") == "yes"
            else ()
        )
    if model.mode == "box_parallel_plane_angle":
        source = {
            "side": "e32531aa-e8dd-49b3-8153-d4d7d5e3fb94",
            "top": "5a2852e9-f360-4aaf-9061-9ab11604a79c",
            "base": "3b655152-9c11-472d-8de0-12f5df83e8ba",
        }[model.names[0]]
        return (("solution", "image_1", source),)
    return ROLES.get(model.mode)
