"""Circular-solid proof roles retain the methods of each reviewed parent."""

from dataclasses import replace

from ..core.errors import ContentPlanError

RULES = {
    "solid-concentric-sphere-parallel-section-area": "concentric_sphere_parallel_section_area",
    "solid-cylinder-axis-chord-angle-distance": "cylinder_axis_chord_geometry",
    "solid-cylinder-axis-chord-lateral-area": "cylinder_axis_chord_geometry",
    "solid-hexagonal-pyramid-insphere-area": "hexagonal_pyramid_insphere_area",
    "solid-cylinder-chord-rectangle-pyramid-volume": "cylinder_chord_rectangle_pyramid_volume",
}
ROLES = {
    "concentric_sphere_parallel_section_area": (
        ("solution", "image_1", "8bf6998a-115e-41a6-8100-d5366d0b2e8e"),
    ),
    "cylinder_axis_chord_geometry": (
        ("solution", "image_1", "0c4a9dfb-2320-4701-9835-af73aadfb9d0"),
        ("solution", "image_2", "7b9ae11b-2b45-4730-ba03-b701d7d9cc58"),
    ),
    "hexagonal_pyramid_insphere_area": (
        ("solution", "image_1", "4b6cc7cf-082f-4cef-bcdb-e8ec2bcc4fb1"),
    ),
    "cylinder_chord_rectangle_pyramid_volume": (
        ("solution", "image_1", "7223215f-0f25-4d53-a62b-075a17f83193"),
    ),
}


def reviewed_model(model, assets, parent_sources, figures):
    if model.mode != "cylinder_axis_chord_geometry":
        return None
    styles = {
        figures[source]["coordinate_method"]
        for source in parent_sources
        if source in figures and "coordinate_method" in figures[source]
    }
    if not styles:
        styles = {
            figures[a["asset_id"]]["coordinate_method"]
            for a in assets.values()
            if "coordinate_method" in figures[a["asset_id"]]
        }
    if len(styles) > 1 or not styles <= {"yes", "no"}:
        raise ContentPlanError("the cylinder parent has ambiguous proof methods")
    style = next(iter(styles)) if styles else model.symbols["coordinate_method"]
    if any(
        figures[a["asset_id"]].get("purpose") == "coordinate" for a in assets.values()
    ):
        style = "yes"
    return replace(model, symbols=model.symbols | {"coordinate_method": style})


def roles(model):
    if (
        model.mode == "cylinder_axis_chord_geometry"
        and model.symbols["coordinate_method"] == "no"
    ):
        return (("solution", "image_1", "4cad92bc-7ad5-4795-85f1-34dba7a08ac9"),)
    return ROLES.get(model.mode)


GROUPS = (
    (
        "502115",
        "f8426f4d-2410-4c01-b6e3-0f98ed7e2e31",
        0,
        "Сечения круглых тел",
        11,
        "08fd7489-6c31-4033-b61d-337a5fa9105f",
        "solid-concentric-sphere-parallel-section-area",
    ),
    (
        "520803",
        "3ba17e58-3770-4542-88bb-b48f3dc1a646",
        13,
        "Круглые тела: цилиндр, конус, шар",
        12,
        "9962704c-136d-4d66-b4bf-cfdf1120e815",
        "solid-cylinder-axis-chord-angle-distance",
    ),
    (
        "520938",
        "8a886851-7313-44d8-ad90-c2dc2e354d6a",
        16,
        "Круглые тела: цилиндр, конус, шар",
        12,
        "9962704c-136d-4d66-b4bf-cfdf1120e815",
        "solid-cylinder-axis-chord-lateral-area",
    ),
    (
        "502023",
        "03a0d45c-6129-4d4e-ad58-99a6c14a7f98",
        0,
        "Комбинации фигур",
        13,
        "0b968753-f499-45a8-b715-8f8249091299",
        "solid-hexagonal-pyramid-insphere-area",
    ),
    (
        "514026",
        "6207aeb6-4582-4efb-b5be-5ba733312281",
        6,
        "Комбинации фигур",
        13,
        "0b968753-f499-45a8-b715-8f8249091299",
        "solid-cylinder-chord-rectangle-pyramid-volume",
    ),
)
