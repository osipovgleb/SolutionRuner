"""Reviewed volume cuts, face angles and line projections share the spatial runtime."""

from dataclasses import replace

RULES = {
    "solid-triangle-prism-half-volume-angle": "triangle_prism_half_volume_angle",
    "solid-triangle-pyramid-face-cosine-angle": "triangle_pyramid_face_cosine_angle",
    "solid-box-tetrahedron-line-projection-angle": "box_tetrahedron_line_projection_angle",
    "solid-rectangular-pyramid-proved-altitude-angle": (
        "rectangular_pyramid_angle",
        "rectangular_pyramid_proved_altitude_angle",
    ),
}
ROLES = {
    "triangle_prism_half_volume_angle": (
        ("solution", "image_1", "32110163-bb47-4e23-a08c-cfbec84ed1ec"),
    ),
    "triangle_pyramid_face_cosine_angle": (
        ("solution", "image_1", "f6e96c0f-fcfa-4458-9699-f4584ee24771"),
    ),
    "box_tetrahedron_line_projection_angle": (
        ("solution", "image_1", "dbdc0dfd-d4ea-4e0f-81db-ccece56df857"),
    ),
    "rectangular_pyramid_proved_altitude_angle": (
        ("solution", "image_1", "7f8c10d5-2ffe-4a50-9256-8ca04937be66"),
    ),
}
PARENT_PROJECTION = "95be579c-68a8-4ebd-83c3-c6eebd9eeffc"
MEDIAN = "61e739a4-ca4c-406e-9326-224e80d05752"
COORDINATES = "c87426df-06cb-4f81-b349-ceda60942944"
DIAGRAM_BUILDERS = {
    "solid-rectangular-pyramid-proved-altitude-angle": "solution_runner.pipelines.solids.line_projection_sources:proved_altitude_diagrams",
}


def proved_altitude_diagrams(context):
    from .distance_figures import diagram_specs

    return diagram_specs(context, preferred_sources=(PARENT_PROJECTION,))


def reviewed_model(model, assets, preferred_sources):
    sources = {a["asset_id"] for a in assets.values()} | set(preferred_sources)
    if model.mode == "rectangular_pyramid_angle" and PARENT_PROJECTION in sources:
        return replace(model, symbols={"scene_family": "proved_vertex_projection"})
    if model.mode == "rectangular_pyramid_proved_altitude_angle":
        return replace(
            model,
            symbols={
                "method": "median"
                if sources & {MEDIAN, COORDINATES}
                else "extended_side",
                "second_figure": "yes" if "image_2" in assets else "no",
            },
        )
    return None


def roles(model):
    if (
        model.mode == "box_tetrahedron_line_projection_angle"
        and model.names[0] == "diagonal"
    ):
        return (("solution", "image_1", "8998638f-ee72-4ad1-b17f-d0f27d7a7bc0"),)
    if (
        model.mode == "rectangular_pyramid_proved_altitude_angle"
        and model.symbols.get("method") == "median"
    ):
        return (("solution", "image_1", MEDIAN),) + (
            (("solution", "image_2", COORDINATES),)
            if model.symbols.get("second_figure") == "yes"
            else ()
        )
    return ROLES.get(model.mode)


GROUPS = (
    (
        "500064",
        "e0f7e9f5-cbf7-4470-9244-46b916e1a2be",
        13,
        "Угол между плоскостями граней многогранника",
        7,
        "491f66c5-a69f-4a6c-a153-ae62d9f76d06",
        "solid-triangle-prism-half-volume-angle",
    ),
    (
        "505237",
        "90b98300-43ef-4bf9-92c7-22b246dc6f70",
        15,
        "Угол между плоскостями граней многогранника",
        7,
        "491f66c5-a69f-4a6c-a153-ae62d9f76d06",
        "solid-triangle-pyramid-face-cosine-angle",
    ),
    (
        "507576",
        "0d0d1f1f-aba4-4efd-a05f-ce575e09a76a",
        0,
        "Угол между прямой и плоскостью",
        8,
        "6a0a2bae-d44e-404e-a770-89f4f5517cde",
        "solid-box-tetrahedron-line-projection-angle",
    ),
    (
        "513098",
        "f1005eec-4de6-4873-8e78-37c661aa2567",
        3,
        "Угол между прямой и плоскостью",
        8,
        "6a0a2bae-d44e-404e-a770-89f4f5517cde",
        "solid-rectangular-pyramid-proved-altitude-angle",
    ),
)
