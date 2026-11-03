"""Preserve complete mixed-image ownership and draw the actual altitude geometry."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...triangles.isosceles.planner import _section
from ...triangles.isosceles.side_altitude_figures import _identity, condition_changes
from ..parallelogram.midpoint_figures import _attach
from ..quantity_content import read_content
from .isosceles_model import read_question
from .isosceles_svg import CE, MARKED, PLAIN, figure_svg
from .quantity_sources import PARENTS, source_bytes

CE_BARE = "46d25626-a77d-4eaf-bcef-1bb477ec17e0"
MARKED_BARE = "3be35d9e-e571-40e8-8a82-e1a0366359ac"
PLAIN_BARE = "590b89bd-3f93-494c-a26c-e162137e6f71"
PREFIX = "iso_trapezoid_"
CONDITION_KEY = PREFIX + "ce_condition"
CE_SOLUTION_KEY = PREFIX + CE
GENERATED_KEYS = {CONDITION_KEY, CE_SOLUTION_KEY, PREFIX + MARKED, PREFIX + PLAIN}
BARE = {CE_BARE, MARKED_BARE, PLAIN_BARE, "c37ee594-116d-4c12-ab84-5fb6f074d03c"}
ALIASES = {"157aa0f8-ea5d-419c-b075-9864f88d2a85": MARKED}


def _seed(asset):
    key = asset["asset_key"]
    source = (
        asset["asset_id"]
        if key in {"image_1", "image_2"}
        else CE
        if key == CONDITION_KEY
        else key.removeprefix(PREFIX)
    )
    source = ALIASES.get(source, source)
    source_bytes(source)
    return source


def selection(context):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", *GENERATED_KEYS}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete trapezoid condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one trapezoid condition image is supported")
    source = images[0]["data-asset-id"] if images else None
    if images:
        images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), source)
    ce = model.mode in {
        "sine",
        "cosine_leg",
        "small_sine",
        "tangent_height",
        "large_tangent",
        "tangent",
    }
    bare = (
        CE_BARE
        if ce
        else PLAIN_BARE
        if model.mode == "height_fortyfive"
        else MARKED_BARE
    )
    height = CE if ce else PLAIN if model.mode == "height_fortyfive" else MARKED
    seeds = {key: _seed(a) for key, a in assets.items()}
    allowed = (
        {bare, height, "c37ee594-116d-4c12-ab84-5fb6f074d03c"}
        if height == MARKED
        else {bare, height}
    )
    if set(seeds.values()) - allowed:
        raise ContentPlanError("the trapezoid assets depict another reviewed method")
    bare_assets = [a for key, a in assets.items() if seeds[key] in BARE]
    height_assets = [a for key, a in assets.items() if seeds[key] not in BARE]
    if len(bare_assets) > 1 or len(height_assets) > 1:
        raise ContentPlanError("duplicate trapezoid condition or altitude figures")
    if any(owners[a["asset_key"]] != "condition" for a in bare_assets):
        raise ContentPlanError("a bare trapezoid belongs in the condition")
    condition_only = ce and not bare_assets
    if not condition_only and any(
        owners[a["asset_key"]] != "solution" for a in height_assets
    ):
        raise ContentPlanError("the construction belongs in the solution")
    key = CONDITION_KEY if condition_only else PREFIX + height
    diagram = spec(key, figure_svg(model, height))
    return (
        model,
        condition,
        bare_assets,
        height_assets,
        bare,
        height,
        diagram,
        condition_only,
    )


def diagram_specs(context):
    return (selection(context)[6],)


def prepare(context, rule, generated):
    (
        model,
        condition,
        bare_assets,
        height_assets,
        bare,
        height,
        diagram,
        condition_only,
    ) = selection(context)
    identifier, url = _identity(diagram["asset_key"], height, diagram, generated)
    current = height_assets[0] if height_assets else None
    if condition_only:
        changes = condition_changes(
            context, condition, current or {}, CONDITION_KEY, identifier, url
        )
        return model, changes, {}, ()
    primary = PARENTS[rule][0]
    bare_source = (
        bare_assets[0]["asset_id"]
        if bare_assets
        else primary
        if primary in BARE
        else bare
    )
    source_bytes(bare_source)
    changes = list(
        condition_changes(
            context,
            condition,
            bare_assets[0] if bare_assets else {},
            "image_1",
            bare_source,
            "/assets/" + bare_source,
        )
    )
    image, delta = _attach(current, diagram["asset_key"], identifier, url, "solution")
    # The shared condition helper removes image_2; the construction replacement owns it here.
    changes = [t for t in changes if t["transformation_target_id"] != "asset:image_2"]
    changes.extend(delta)
    return (
        model,
        tuple(changes),
        {"height": "<center>" + image + "</center>"},
        (diagram["asset_key"],),
    )
