"""Reuse complete unnumbered chord and tangent diagrams with strict ownership."""

from . import static_figures
from .tangent_model import read_question

TANGENTS = (
    "d6035e07-cca6-4352-80a7-e671530a4363",
    "ce2fa07b-34f1-44dc-833f-deb1f5d7af2d",
)
SOURCES = {
    "chord_thirty": ("03407436-f0c4-4cab-aaf7-d1ac07758183",),
    "chord_obtuse": ("ba29ffaf-2266-4074-8d9a-b0af840fa294",),
    "arc_ratio": ("fa9b1335-5d14-421c-ad1f-f75492af3f92",),
    "tangent_chord": ("1fdab1cc-720e-4514-b05d-d9163cbf99dd",),
    "central_from_tangent": TANGENTS,
    "two_tangents_angle": TANGENTS,
    "two_tangents_arc": TANGENTS,
    "near_angle": ("04c45fcc-f49e-434f-b8fe-b3254ed2719a",),
    "near_arc": ("04c45fcc-f49e-434f-b8fe-b3254ed2719a",),
    "far_angle": ("9d345fef-61ad-4320-ae6c-980925039824",),
    "far_arc": ("9d345fef-61ad-4320-ae6c-980925039824",),
}
DETAILS = {
    "chord_thirty": "37a12d63-5fb7-446e-9cad-41be89cdaaa5",
    "chord_obtuse": "cebe4bd3-9c4c-47ff-962d-bdd8515f4933",
    "central_from_tangent": TANGENTS[1],
}
LEGACY_TANGENT = "22cfa237-3e19-4574-8062-5929258e12ab"


PICTURES = {mode: (("detail", source),) for mode, source in DETAILS.items()}
ALIASES = {TANGENTS[1]: (LEGACY_TANGENT,)}


def selection(context):
    return static_figures.selection(context, read_question, SOURCES, PICTURES, ALIASES)


def diagram_specs(context):
    selection(context)
    return ()


def prepare(context, generated):
    return static_figures.prepare(
        context, generated, read_question, SOURCES, PICTURES, ALIASES
    )
