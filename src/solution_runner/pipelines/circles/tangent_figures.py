"""Reuse complete unnumbered chord and tangent diagrams with strict ownership."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .quantity_sources import source_bytes
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


def selection(context):
    content, assets, owners = read_content(context, {"image_1", "image_2"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete chord or tangent condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one chord or tangent condition figure is supported")
    model = read_question(str(soup), images[0]["data-asset-id"] if images else None)
    for key, asset in assets.items():
        allowed = (
            SOURCES[model.mode] if key == "image_1" else (DETAILS.get(model.mode),)
        )
        if key == "image_2" and model.mode == "central_from_tangent":
            allowed += (LEGACY_TANGENT,)
        if asset["asset_id"] not in allowed or owners[key] != (
            "condition" if key == "image_1" else "solution"
        ):
            raise ContentPlanError(
                "the chord or tangent figure depicts another method or owner"
            )
        source_bytes(asset["asset_id"])
    for source in (
        *SOURCES[model.mode],
        *((DETAILS[model.mode],) if model.mode in DETAILS else ()),
    ):
        source_bytes(source)
    return model, condition, assets


def diagram_specs(context):
    selection(context)
    return ()


def prepare(context, generated):
    model, condition, assets = selection(context)
    if generated:
        raise ContentPlanError(
            "compatible chord and tangent figures need no generated copies"
        )
    current = assets.get("image_1", {})
    source = current.get("asset_id", SOURCES[model.mode][0])
    changes = list(
        condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
    )
    if model.mode not in DETAILS:
        return model, tuple(changes), {}, ()
    changes = [t for t in changes if t["transformation_target_id"] != "asset:image_2"]
    detail = DETAILS[model.mode]
    image, delta = _attach(
        assets.get("image_2"), "image_2", detail, "/assets/" + detail, "solution"
    )
    return (
        model,
        tuple(changes) + tuple(delta),
        {"detail": "<center>" + image + "</center>"},
        ("image_2",),
    )
