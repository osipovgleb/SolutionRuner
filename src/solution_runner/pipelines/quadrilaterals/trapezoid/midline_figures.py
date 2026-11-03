"""Reuse audited unnumbered diagrams with exact property and ownership checks."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...triangles.isosceles.planner import _section
from ...triangles.isosceles.side_altitude_figures import condition_changes
from ..parallelogram.midpoint_figures import _attach
from ..quantity_content import read_content
from .midline_model import read_question
from .quantity_sources import source_bytes

DETAIL = "cba9307b-727e-42e2-b2a7-29d6ad501c31"
SOURCES = {
    "angle_difference": ("3be35d9e-e571-40e8-8a82-e1a0366359ac",),
    "large_base": ("2d5e6a8f-e987-4de5-a714-a05c39e6700b",),
    "diagonal_piece": ("18705ade-6142-4b59-af59-6f7b7ada9af7",),
    "cut_perimeter": (
        "58dcfe8c-cfbb-4aee-8e48-060acaa9f0af",
        "e32a4336-7ffb-4fb4-bf6c-e979316d6e6a",
    ),
    "base_parts": ("fc0d0177-148c-48b1-a8da-a25a5a72a6cc",),
    "perimeter_midline": (
        "bb0a47c4-4d4b-4e42-be3b-18afb98da371",
        "835914ef-4287-4fbc-9c08-0526dfe87936",
    ),
    "diagonal_midpoints": ("f3300198-af16-408a-820a-0ec46476be90",),
    "perpendicular": ("700ce947-e033-41d3-bddb-4b72b949870e",),
}


def selection(context):
    content, assets, owners = read_content(context, {"image_1", "image_2"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete trapezoid scalar condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one trapezoid scalar condition figure is supported")
    model = read_question(str(soup), images[0]["data-asset-id"] if images else None)
    for key, asset in assets.items():
        allowed = SOURCES[model.mode] if key == "image_1" else (DETAIL,)
        if (
            asset["asset_id"] not in allowed
            or owners[key] != ("condition" if key == "image_1" else "solution")
            or (key == "image_2" and model.mode != "diagonal_midpoints")
        ):
            raise ContentPlanError("the scalar trapezoid figure depicts another method")
        source_bytes(asset["asset_id"])
    for source in SOURCES[model.mode]:
        source_bytes(source)
    if model.mode == "diagonal_midpoints":
        source_bytes(DETAIL)
    return model, condition, assets


def diagram_specs(context):
    selection(context)
    return ()


def prepare(context, rule, generated):
    model, condition, assets = selection(context)
    if generated:
        raise ContentPlanError("reviewed static trapezoids need no generated assets")
    current = assets.get("image_1", {})
    source = current.get("asset_id", SOURCES[model.mode][0])
    changes = list(
        condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
    )
    if model.mode != "diagonal_midpoints":
        return model, tuple(changes), {}, ()
    # The detail replacement owns image_2; do not remove it twice.
    changes = [t for t in changes if t["transformation_target_id"] != "asset:image_2"]
    image, delta = _attach(
        assets.get("image_2"), "image_2", DETAIL, "/assets/" + DETAIL, "solution"
    )
    return (
        model,
        tuple(changes) + tuple(delta),
        {"detail": "<center>" + image + "</center>"},
        ("image_2",),
    )
