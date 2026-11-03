"""Prepare topology-correct condition images with explicit, replayable asset changes."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...word_problems.common import rewrite
from ..right.basic_parent import _targeted
from .basic_figures import uncrop_svg
from .side_altitude_model import read_context
from .side_altitude_sources import (
    NOTE_SOURCE,
    ZERO_KEY,
    choose,
    generated_key,
    generated_keys,
    seed,
    source_bytes,
)
from .side_altitude_svg import remapped_svg, zero_svg


def _assets(context, model):
    assets = context["normalized_content"].get("assets")
    if not isinstance(assets, list) or any(not isinstance(a, dict) for a in assets):
        raise ContentPlanError("side-altitude image metadata must be a list")
    by_key = {a.get("asset_key"): a for a in assets}
    allowed = {"image_1", "image_2", *generated_keys()}
    if len(by_key) != len(assets) or set(by_key) - allowed:
        raise ContentPlanError(
            "unreviewed or duplicate side-altitude assets are present"
        )
    primary = [a for k, a in by_key.items() if k != "image_2"]
    if len(primary) != 1:
        raise ContentPlanError("one primary side-altitude asset is required")
    for asset in assets:
        source = asset.get("asset_id")
        if (
            not isinstance(source, str)
            or not source
            or asset.get("kind") != "ordinary_image"
            or asset.get("url") != "/assets/" + source
        ):
            raise ContentPlanError("side-altitude asset metadata changed")
    seed(primary[0])
    if "image_2" in by_key:
        role = (model.given_kind, model.triangle.function, model.requested_kind)
        allowed_notes = {
            NOTE_SOURCE: ("side", "sin", "projection"),
            "e4647c04-5060-43c8-a3da-5958850c042f": ("side", "sin", "height"),
        }
        note_source = by_key["image_2"]["asset_id"]
        if allowed_notes.get(note_source) != role:
            raise ContentPlanError(
                "the legacy side-altitude note figure is not reviewed"
            )
        source_bytes(note_source)
    return primary[0], by_key


def selection(context):
    model = read_context(context)
    asset, by_key = _assets(context, model)
    mode, source = choose(model, seed(asset))
    if "image_2" in by_key and (mode != "native" or source != asset["asset_id"]):
        attached = by_key["image_2"]["asset_id"]
        candidate_mode, candidate_source = choose(model, attached)
        if candidate_mode == "native" and candidate_source == attached:
            mode, source = candidate_mode, candidate_source
    raw = source_bytes(source)
    if mode == "native":
        return model, asset, mode, "image_1", source, None
    key = ZERO_KEY if mode == "zero" else generated_key(source)
    if mode == "zero":
        svg = zero_svg(model, raw, model.given_kind == "side")
    elif mode == "crop":
        svg = uncrop_svg(raw)
    else:
        svg = remapped_svg(model, raw, model.given_kind == "side")
    return model, asset, mode, key, source, spec(key, svg)


def diagram_specs(context):
    *_, diagram = selection(context)
    return (diagram,) if diagram else ()


def _identity(key, source, diagram, generated):
    if diagram is None:
        if generated:
            raise ContentPlanError(
                "a compatible native side-altitude picture needs no duplicate"
            )
        return source, "/assets/" + source
    if (
        len(generated) != 1
        or generated[0].get("asset_key") != key
        or generated[0].get("sha256") != diagram["sha256"]
    ):
        raise ContentPlanError(
            "the prepared side-altitude SVG differs from the selected geometry"
        )
    item = generated[0]
    identifier = item.get("source_asset_id")
    if (
        not isinstance(identifier, str)
        or not identifier
        or item.get("url") != "/assets/" + identifier
    ):
        raise ContentPlanError("the generated side-altitude identity is invalid")
    return identifier, item["url"]


def prepare(context, condition, generated):
    _model, current, _mode, key, source, diagram = selection(context)
    identifier, url = _identity(key, source, diagram, generated)
    return condition_changes(context, condition, current, key, identifier, url)


def condition_changes(context, condition, current, key, identifier, url):
    """Replace a reviewed condition picture without changing the question text."""
    old_key = current.get("asset_key", "")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1 or (
        images
        and (
            images[0].get("data-asset-key") != old_key
            or images[0].get("data-asset-id") != current["asset_id"]
            or images[0].get("data-transformation-target-id") != "asset:" + old_key
        )
    ):
        raise ContentPlanError(
            "the condition image differs from its side-altitude metadata"
        )
    if condition.get("asset_keys") != ([old_key] if images else []):
        raise ContentPlanError("side-altitude condition keys differ from its markup")
    changes = []
    if not images or (key, identifier) != (old_key, current["asset_id"]):
        image = BeautifulSoup('<img alt=""/>', "html.parser").img
        image["data-asset-key"] = key
        image["data-asset-id"] = identifier
        image["src"] = url
        image["data-transformation-target-id"] = "asset:" + key
        if images:
            images[0].replace_with(image)
        elif soup.find("p"):
            soup.find("p").insert(0, image)
        else:
            soup.insert(0, image)
        changes.append(
            {
                "transformation_target_id": "asset:" + key,
                "operation": "rewrite" if key == old_key else "add",
                "value": {
                    "asset_key": key,
                    "asset_id": identifier,
                    "url": url,
                    "kind": "ordinary_image",
                    "alt": "",
                    "parent_target_id": _targeted(condition)[
                        "transformation_target_id"
                    ],
                    "position": 0,
                    "html": str(image),
                },
            }
        )
        change = rewrite(
            _targeted(condition),
            "condition",
            condition.get("title", "Условие"),
            str(soup),
        )
        change["value"]["asset_keys"] = [key]
        changes.append(change)
        if old_key and old_key != key:
            changes.append(
                {"transformation_target_id": "asset:" + old_key, "operation": "remove"}
            )
    if any(
        a.get("asset_key") == "image_2" for a in context["normalized_content"]["assets"]
    ):
        changes.append(
            {"transformation_target_id": "asset:image_2", "operation": "remove"}
        )
    return tuple(changes)
