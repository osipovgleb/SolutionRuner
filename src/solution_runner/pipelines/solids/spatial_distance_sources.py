"""Pins and exact numeric compatibility for the proof-and-distance methods."""

import json
from dataclasses import replace
from importlib.resources import files

DATA = json.loads(
    files(__package__).joinpath("assets/spatial-distance-sources.json").read_text()
)
RULES = {
    "solid-triangle-pyramid-vertical-midsection": "triangle_vertical_section_area",
    "solid-pyramid-reflected-apex-section": (
        "reflected_triangle_section_midline",
        "reflected_square_section_midline",
    ),
    "solid-square-pyramid-centroid-section": "square_median_section_area",
    "solid-triangle-pyramid-perpendicular-section": "triangle_perpendicular_section_area",
    "solid-cube-midplane-volume-distance": (
        "cube_base_plane_distance",
        "cube_vertical_plane_distance",
    ),
    "solid-rectangular-pyramid-parallel-section": "pyramid_parallel_section_height",
    "solid-triangle-pyramid-bisector-section": (
        "triangle_bisector_section_edge",
        "triangle_bisector_section_area",
    ),
    "solid-square-pyramid-parallel-section": (
        "pyramid_parallel_section_area",
        "pyramid_parallel_section_angle",
    ),
    "solid-rectangular-pyramid-altitude": (
        "rectangular_pyramid_distance",
        "rectangular_pyramid_angle",
    ),
    "solid-square-pyramid-midplane": "square_midplane_distance",
    "solid-triangle-pyramid-face-distance": "triangle_face_distance",
    "solid-prism-section-normal": (
        "square_prism_section_distance",
        "triangle_prism_section_distance",
    ),
    "solid-prism-projection-height": "prism_projection_height",
    "solid-pyramid-skew-line-height": "pyramid_skew_height",
    "solid-hexagonal-prism-plane-distance": "hex_prism_distance",
    "solid-tetrahedron-ratio-section": ("ratio_plane_distance", "ratio_plane_angle"),
    "solid-tetrahedron-midpoint-distance": "tetra_midpoint_distance",
    "solid-hexagonal-pyramid-point-line-distance": "hex_vertex_line_distance",
    "solid-prism-plane-symmetry-altitude": "prism_plane_altitude",
    "solid-prism-square-skew-distance": "prism_square_skew",
    "solid-pyramid-skew-midpoint-distance": "pyramid_skew_midpoint",
    "solid-box-altitude-distance-comparison": "box_altitude_comparison",
}
PARENTS = {
    rule: (primary, tuple(tuple(f) for f in figures), digest)
    for rule, (primary, figures, digest) in DATA["parents"].items()
}
SOURCES = {
    source: (entry["canonical"], entry["sha256"])
    for source, entry in DATA["figures"].items()
}


def modes(entry):
    return entry.get("modes") or (entry["mode"],)


MODE_SOURCES = {
    mode: tuple(
        source for source, entry in DATA["figures"].items() if mode in modes(entry)
    )
    for allowed in RULES.values()
    for mode in ((allowed,) if isinstance(allowed, str) else allowed)
}
GENERATED_MODES = {
    "box_altitude_comparison",
    "hex_vertex_line_distance",
    "ratio_plane_distance",
}

ROLES = {
    "triangle_vertical_section_area": (
        ("solution", "image_1", "6ceb8276-18bf-4e14-bf44-a2386fc9d27d"),
    ),
    "reflected_triangle_section_midline": (
        ("solution", "image_1", "2e526a67-1049-4f21-b7a6-8f593ed97c6d"),
    ),
    "reflected_square_section_midline": (
        ("solution", "image_1", "0bcf83c6-133d-4245-8170-c9b5d153fb68"),
    ),
    "square_median_section_area": (
        ("solution", "image_1", "5e419167-6d4e-4098-bddd-9fd5345e49b8"),
    ),
    "triangle_perpendicular_section_area": (
        ("solution", "image_1", "27f83f0e-09f6-4361-9f69-3c3e0233f1ce"),
    ),
    "cube_base_plane_distance": (
        ("solution", "image_1", "554860bc-05fd-4543-a1a5-033b62595aaf"),
        ("solution", "image_2", "a0825224-ae99-467c-8821-f211cdd4f66d"),
    ),
    "cube_vertical_plane_distance": (
        ("solution", "image_1", "b71f92af-059b-431f-86e5-210da544f331"),
        ("solution", "image_2", "d1ee9696-4e38-4ef0-9634-f685fa36446b"),
    ),
    "pyramid_parallel_section_height": (
        ("solution", "image_1", "83267fa9-e42c-43a6-8954-fcbd9451ab25"),
    ),
    "triangle_bisector_section_edge": (
        ("solution", "image_1", "fa6eb3eb-f0aa-4db0-ad43-b80685420ef9"),
    ),
    "triangle_bisector_section_area": (
        ("solution", "image_1", "fa6eb3eb-f0aa-4db0-ad43-b80685420ef9"),
    ),
    "pyramid_parallel_section_area": (
        ("solution", "image_1", "b0161b2a-665d-4e9d-8da8-49431e26eeac"),
        ("solution", "image_2", "b062f3b9-4d51-4cd9-9b17-05ec47180101"),
    ),
    "pyramid_parallel_section_angle": (
        ("solution", "image_1", "ff8131d0-eddf-40d3-ab66-d2c57ea797f1"),
    ),
    "rectangular_pyramid_distance": (
        ("solution", "image_1", "38d4bcc9-4139-426b-aadd-a55612638acd"),
    ),
    "rectangular_pyramid_angle": (
        ("solution", "image_1", "66526bdf-211e-4a30-8e65-3f13ce943532"),
    ),
    "square_midplane_distance": (
        ("solution", "image_1", "7e5eabca-f3fc-4bfb-b6a3-a48775d6b33d"),
    ),
    "triangle_face_distance": (
        ("solution", "image_1", "f8485d85-4f02-4a3b-b3b8-750be3b499ed"),
    ),
    "square_prism_section_distance": (
        ("solution", "image_1", "ce166516-5e3d-42c1-be4e-0fc07104c4fd"),
        ("solution", "image_2", "5fbbe405-465a-40ed-9a14-c4f65f363e67"),
    ),
    "triangle_prism_section_distance": (
        ("solution", "image_1", "50282a94-50ed-43ef-978b-cf588e729eb8"),
        ("solution", "image_2", "42646b8c-2500-46f0-ab75-7b21e691d63d"),
    ),
    "prism_projection_height": (
        ("solution", "image_1", "998c63f7-b9eb-4cf0-9724-d5963101e87d"),
    ),
    "pyramid_skew_height": (
        ("solution", "image_1", "7961e813-abe2-4665-bfb3-458586d658af"),
    ),
    "hex_prism_distance": (
        ("solution", "image_1", "47fb6f56-165b-40e5-9374-398da1181862"),
        ("solution", "image_2", "91162f76-b15f-48c4-99c6-d90ac473c71e"),
    ),
    "ratio_plane_distance": (
        ("solution", "image_1", "347eebde-bcea-4a26-82e2-c4d2706cb665"),
    ),
    "ratio_plane_angle": (
        ("solution", "image_1", "3bb014eb-a647-4acc-8ada-d83a1afc2a2d"),
    ),
    "tetra_midpoint_distance": (
        ("solution", "image_1", "0a3e798d-87fb-4252-ad25-90fd23341788"),
    ),
    "hex_vertex_line_distance": (
        ("solution", "image_1", "53d5a0fe-92ff-4f89-824b-742396ce61dc"),
    ),
    "prism_plane_altitude": (
        ("solution", "image_1", "899d2fbf-54d9-4d31-847d-7e9e6242ee0b"),
    ),
    "prism_square_skew": (
        ("solution", "image_1", "8a9c6676-fa04-4271-a557-ccf630c55a82"),
        ("solution", "image_2", "49c3c8ca-95e7-4db4-80e3-981300897954"),
    ),
    "pyramid_skew_midpoint": (
        ("solution", "image_1", "16d52d78-d4d3-43e0-9ab5-ea217c799774"),
        ("solution", "image_2", "8a358169-39ce-4e35-bdba-78122985875f"),
    ),
    "box_altitude_comparison": (
        ("solution", "image_1", "dfdd3600-d13b-435b-a4fc-3623ec28af6c"),
    ),
}


def compatible(model, source, role, slot):
    entry = DATA["figures"].get(source)
    if (
        not entry
        or role != "solution"
        or model.mode not in modes(entry)
        or entry["slot"] != slot
    ):
        return False
    if model.mode == "ratio_plane_distance" and entry.get(
        "method"
    ) != model.symbols.get("method"):
        return False
    if entry.get("reusable") is False:
        return False
    if entry.get("top_foot") and not (0 < model.q["foot"] < 1):
        return False
    if "names_prefix" in entry and entry["names_prefix"] != list(
        model.names[: len(entry["names_prefix"])]
    ):
        return False
    if "names" in entry and entry["names"] != list(model.names):
        return False
    if entry.get("interior") and not (0 < model.q["foot"] < 1):
        return False
    return "squares" not in entry or (
        entry["squares"] == [str(v) for v in model.squares]
        and entry["names"] == list(model.names)
    )


def reviewed_model(model, assets):
    if model.mode in {
        "square_prism_section_distance",
        "triangle_prism_section_distance",
    }:
        source = assets["image_1"]["asset_id"] if "image_1" in assets else None
        entry = DATA["figures"].get(source)
        return replace(model, symbols=entry["symbols"] if entry else {})
    if model.mode != "ratio_plane_distance":
        return model
    source = assets["image_1"]["asset_id"] if "image_1" in assets else None
    entry = DATA["figures"].get(source)
    method = entry["method"] if entry and "method" in entry else "perpendicular"
    if "image_2" in assets:
        method = "cross_section"
    return replace(model, symbols={"method": method})


def roles(model):
    if (
        model.mode == "triangle_prism_section_distance"
        and model.symbols.get("section_layout") == "midpoints"
    ):
        return ROLES[model.mode][:1]
    if (
        model.mode == "ratio_plane_distance"
        and model.symbols.get("method") == "cross_section"
    ):
        return (
            ("solution", "image_1", "3bb014eb-a647-4acc-8ada-d83a1afc2a2d"),
            ("solution", "image_2", "5a015c60-a807-463f-a5d0-497b80f85aa9"),
        )
    return ROLES[model.mode]


def allowed_keys(mode):
    return {DATA["figures"][source]["slot"] for source in MODE_SOURCES[mode]}


def with_symbols(model, source):
    entry = DATA["figures"].get(source, {})
    return replace(model, symbols=model.symbols | entry.get("symbols", {}))
