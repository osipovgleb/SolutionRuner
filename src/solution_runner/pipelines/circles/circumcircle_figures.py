"""Reuse the exact regular-triangle circumcircle constructions."""

from ..core.errors import ContentPlanError
from ..triangles.isosceles.side_altitude_figures import condition_changes
from . import static_figures
from .circumcircle_model import read_question

ACUTE = ("f0cf673f-8658-42ed-a2e3-58b4debfd315", "76a7c802-b4a8-4880-af3c-e4e7855a95f9")
RIGHT = ("a124add8-430b-4761-ad72-2f022dc85c73",)
OBTUSE = (
    "0676249d-0639-4ff4-9c2b-bdfacc3f5390",
    "8498fd3b-9859-41b8-b9fc-df1e9c030e93",
    "e5506a55-6c96-4c42-b5bd-b826625e6e4f",
)
SOURCES = {
    "right_radius": RIGHT,
    "right_hypotenuse": RIGHT,
    "right_legs": RIGHT,
    "isosceles_diameter": ("3607b526-1d2a-4e3b-a75d-fbcf5e3daf27",),
    "hexagon_side": ("7fd8d21d-a828-4f8a-85d3-9a0ee75cfbc2",),
    "hexagon_diameter": ("fa1bc6d0-29ea-4a5f-b993-740152b343d8",),
    "sine_radius": ACUTE + RIGHT + OBTUSE,
    "sine_side": ACUTE + RIGHT + OBTUSE,
    "radius_side": ("1725d5a4-9cd0-4fc3-903b-b5406c8fa4c0",),
    "side_radius": ("649e19b9-b2f8-4b20-b1dd-d55b8678de65",),
    "radius_height": ("91400a21-c013-48da-a644-d3bde6a3c153",),
    "height_radius": ("880b35c8-fb7d-462e-b041-a41ddce9bd5a",),
}


DETAILS = {"hexagon_side": (("equilateral", "da152d89-1c61-4571-a592-42f5eb10c818"),)}


def diagram_specs(context):
    static_figures.selection(context, read_question, SOURCES, DETAILS, {})
    return ()


def prepare(context, generated):
    model, condition, assets = static_figures.selection(
        context, read_question, SOURCES, DETAILS, {}
    )
    if model.mode in {"sine_radius", "sine_side"}:
        if generated:
            raise ContentPlanError(
                "compatible circumcircle pictures need no generated copies"
            )
        current = assets.get("image_1", {})
        angle = model.given[1]
        allowed = ACUTE if angle < 90 else RIGHT if angle == 90 else OBTUSE
        source = current.get("asset_id")
        if source not in allowed:
            source = allowed[0]
        changes = condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
        return model, changes, {}, ()
    return static_figures.prepare(
        context, generated, read_question, SOURCES, DETAILS, {}
    )
