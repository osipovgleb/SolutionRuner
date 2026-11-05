"""Pins and exact numeric compatibility for the proof-and-distance methods."""

import json
from importlib.resources import files

DATA = json.loads(
    files(__package__).joinpath("assets/spatial-distance-sources.json").read_text()
)
RULES = {
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
ROLES = {
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
    return "squares" not in entry or (
        entry["squares"] == [str(v) for v in model.squares]
        and entry["names"] == list(model.names)
    )
