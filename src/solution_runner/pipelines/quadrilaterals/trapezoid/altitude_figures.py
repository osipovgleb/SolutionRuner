"""Prepare both actual condition and solution diagrams with strict asset ownership."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...triangles.isosceles.planner import _section
from ...triangles.isosceles.side_altitude_figures import _identity, condition_changes
from ..parallelogram.midpoint_figures import _attach
from ..quantity_content import read_content
from .altitude_model import read_question
from .altitude_svg import PAIRS, figure_svg
from .quantity_sources import source_bytes

PREFIX = "trapezoid_altitude_"
SOURCES = {s for pair in PAIRS.values() for s in pair}
GENERATED_KEYS = {PREFIX + s for s in SOURCES}


def selection(context):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", *GENERATED_KEYS}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one trapezoid altitude condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one trapezoid condition figure is supported")
    source = images[0]["data-asset-id"] if images else None
    if images:
        images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), source)
    pair = PAIRS[model.mode]
    selected = {}
    for key, asset in assets.items():
        seed = (
            asset["asset_id"]
            if key in {"image_1", "image_2"}
            else key.removeprefix(PREFIX)
        )
        if seed not in pair:
            raise ContentPlanError(
                "the trapezoid figure depicts another reviewed method"
            )
        source_bytes(seed)
        owner = "condition" if seed == pair[0] else "solution"
        if owners[key] != owner or owner in selected:
            raise ContentPlanError("ambiguous trapezoid altitude figure ownership")
        selected[owner] = asset
    diagrams = tuple(
        spec(PREFIX + source, figure_svg(model, source)) for source in pair
    )
    return model, condition, selected, diagrams


def diagram_specs(context):
    return selection(context)[-1]


def prepare(context, rule, generated):
    model, condition, selected, diagrams = selection(context)
    if len(generated) != 2 or {g.get("asset_key") for g in generated} != {
        d["asset_key"] for d in diagrams
    }:
        raise ContentPlanError(
            "both prepared trapezoid diagrams must match the current geometry"
        )
    changes = []
    pictures = {}
    keys = []
    for owner, drawing in zip(("condition", "solution"), diagrams):
        key = drawing["asset_key"]
        source = key.removeprefix(PREFIX)
        identifier, url = _identity(
            key, source, drawing, tuple(g for g in generated if g["asset_key"] == key)
        )
        current = selected.get(owner)
        if owner == "condition":
            delta = condition_changes(
                context, condition, current or {}, key, identifier, url
            )
            changes.extend(
                t for t in delta if t["transformation_target_id"] != "asset:image_2"
            )
        else:
            image, delta = _attach(current, key, identifier, url, owner)
            changes.extend(delta)
            pictures["height"] = "<center>" + image + "</center>"
            keys.append(key)
    return model, tuple(changes), pictures, tuple(keys)
