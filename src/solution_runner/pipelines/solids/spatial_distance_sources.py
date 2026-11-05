"""Pins and exact numeric compatibility for the proof-and-distance methods."""

import json
from importlib.resources import files

DATA = json.loads(
    files(__package__).joinpath("assets/spatial-distance-sources.json").read_text()
)
RULES = {
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
MODE_SOURCES = {
    mode: tuple(s for s, f in DATA["figures"].items() if f["mode"] == mode)
    for mode in RULES.values()
}
GENERATED_MODES = {"box_altitude_comparison", "hex_vertex_line_distance"}

ROLES = {
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
        or entry["mode"] != model.mode
        or entry["slot"] != slot
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
