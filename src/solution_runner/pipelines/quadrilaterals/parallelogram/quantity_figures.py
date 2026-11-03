"""Validate complete figure ownership and prepare static reuse or actual height SVGs."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...triangles.isosceles.planner import _section
from ...triangles.isosceles.side_altitude_figures import _identity, condition_changes
from ..quantity_content import read_content
from .bisector_figures import prepare as prepare_rhombus
from .bisector_figures import selection as select_rhombus
from .bisector_svg import DOUBLE_SOURCE, RATIO_KEY, RATIO_SOURCE, RHOMBUS_KEY
from .bisector_svg import figure_svg as bisector_svg
from .midpoint_figures import _attach
from .quantity_model import read_question
from .quantity_sources import source_bytes
from .quantity_svg import DETAIL, SINE, figure_svg

REFERENCE = "c45d5a90-41dd-4849-8c26-9289880cecfb"
BARE = "046e3609-22e3-41c4-be82-0f3022ce9151"
RHOMBUS = "0a581314-6063-4c87-95eb-073086a172f4"
SINE_KEY = "quantity_sine_condition"
DETAIL_KEY = "quantity_transfer_detail"


def selection(context):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", SINE_KEY, DETAIL_KEY, RATIO_KEY, RHOMBUS_KEY}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one quantity condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("at most one quantity condition image is supported")
    source = images[0]["data-asset-id"] if images else None
    if images:
        images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), source)
    if model.mode == "rhombus_angle":
        return select_rhombus(model, condition, assets, owners)
    primary = (
        SINE
        if model.mode == "sine"
        else REFERENCE
        if model.mode == "transfer"
        else BARE
        if model.mode in {"height", "angle_sum", "angle_difference"}
        else {
            "sixty_height": "0f9596a2-7160-4a52-8155-cdecf3de5824",
            "sixty_diagonal": "d079942f-59e2-4f99-8e45-e295851aa7c1",
            "ratio_height": "fc78faa7-5ccc-40bd-8519-e9d4a1629853",
            "angle_split": "6bade94c-1b78-4213-a883-6c3f32da00f5",
            "angle_ratio": "fae36b3a-5683-48f0-a5b2-dec9e314795f",
            "side_difference": "fae36b3a-5683-48f0-a5b2-dec9e314795f",
            "side_known": "fae36b3a-5683-48f0-a5b2-dec9e314795f",
            "side_ratio": "fae36b3a-5683-48f0-a5b2-dec9e314795f",
            "bisector_ratio": RATIO_SOURCE,
            "bisector_double": DOUBLE_SOURCE,
        }.get(model.mode, RHOMBUS)
    )
    source_bytes(primary)
    if model.mode == "transfer":
        allowed = {"image_1": REFERENCE, "image_2": DETAIL, DETAIL_KEY: None}
        owner = "solution"
        if "image_2" in assets and DETAIL_KEY in assets:
            raise ContentPlanError("ambiguous corrected height figure")
    else:
        allowed = {"image_1": primary}
        if model.mode == "sine":
            allowed[SINE_KEY] = None
        if model.mode == "bisector_ratio":
            allowed[RATIO_KEY] = None
        if len(assets) > 1:
            raise ContentPlanError("one primary quantity condition image is required")
        owner = "condition"
    for key, asset in assets.items():
        misplaced_primary = (
            owner == "condition" and key == "image_1" and owners[key] == "solution"
        )
        if (
            key not in allowed
            or (owners[key] != owner and not misplaced_primary)
            or (allowed[key] is not None and asset["asset_id"] != allowed[key])
        ):
            raise ContentPlanError(
                "the quantity figure depicts another method or section"
            )
    compatible_detail = model.mode == "transfer" and (
        model.a,
        model.b,
        model.first_height,
        model.second_height,
    ) == (9, 15, 10, 6)
    diagram = (
        spec(SINE_KEY if model.mode == "sine" else DETAIL_KEY, figure_svg(model))
        if model.mode in {"sine", "transfer"} and not compatible_detail
        else None
    )
    if model.mode == "bisector_ratio":
        diagram = spec(RATIO_KEY, bisector_svg(model))
    return model, condition, assets, primary, diagram


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, generated):
    model, condition, assets, primary, diagram = selection(context)
    expected = {diagram["asset_key"]} if diagram else set()
    if (
        len(generated) != len(expected)
        or {g.get("asset_key") for g in generated} != expected
    ):
        raise ContentPlanError(
            "the prepared quantity diagrams differ from the current model"
        )
    if model.mode == "rhombus_angle":
        return prepare_rhombus(model, assets, diagram, generated)
    if model.mode != "transfer":
        current = next(iter(assets.values()), {})
        key = diagram["asset_key"] if diagram else "image_1"
        identifier, url = _identity(key, primary, diagram, generated)
        changes = condition_changes(context, condition, current, key, identifier, url)
        return model, changes, {}, ()
    pictures, changes, keys = {}, [], []
    for part, key, source, drawing, current in (
        ("reference", "image_1", REFERENCE, None, assets.get("image_1")),
        (
            "detail",
            DETAIL_KEY if diagram else "image_2",
            DETAIL,
            diagram,
            assets.get(DETAIL_KEY) or assets.get("image_2"),
        ),
    ):
        identifier, url = _identity(
            key, source, drawing, tuple(g for g in generated if g["asset_key"] == key)
        )
        image, delta = _attach(current, key, identifier, url, "solution")
        pictures[part] = "<center>" + image + "</center>"
        changes.extend(delta)
        keys.append(key)
    return model, tuple(changes), pictures, tuple(keys)
