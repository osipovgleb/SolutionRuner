"""Prepare explicit condition-figure replacements without uploads or attachments."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...word_problems.common import rewrite
from .altitude_parent import _source
from .basic_parent import _targeted
from .construction_angles import SOURCES, read_context
from .construction_svg import SOURCE_HASHES, figure_svg

GENERATED_KEY = "construction_condition"


def diagram_specs(context):
    model = read_context(context)
    if model.topology > 0:
        return ()
    return (spec(GENERATED_KEY, figure_svg(model.pair, model.topology)),)


def _current(content, condition):
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one ordinary construction condition image is required")
    asset = assets[0]
    key, source = asset.get("asset_key"), asset.get("asset_id")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        key not in {"image_1", GENERATED_KEY}
        or not isinstance(source, str)
        or not source
        or (key == "image_1" and source not in SOURCE_HASHES)
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != "/assets/" + source
        or condition.get("asset_keys") != [key]
        or len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != source
        or images[0].get("data-transformation-target-id") != "asset:" + key
    ):
        raise ContentPlanError("the construction figure metadata or reference changed")
    return asset, soup, images[0]


def _desired(model, generated):
    if model.topology > 0:
        if generated:
            raise ContentPlanError(
                "a compatible existing construction needs no generated duplicate"
            )
        source = SOURCES[model.pair]
        _source(source, sources=SOURCE_HASHES)
        return "image_1", source, "/assets/" + source
    specs = (spec(GENERATED_KEY, figure_svg(model.pair, model.topology)),)
    if (
        len(generated) != 1
        or generated[0].get("asset_key") != GENERATED_KEY
        or generated[0].get("sha256") != specs[0]["sha256"]
        or not generated[0].get("source_asset_id")
        or generated[0].get("url") != "/assets/" + generated[0]["source_asset_id"]
    ):
        raise ContentPlanError(
            "the prepared condition SVG must match the exact construction branch"
        )
    return GENERATED_KEY, generated[0]["source_asset_id"], generated[0]["url"]


def prepare_figure(content, condition, model, generated):
    current, soup, image = _current(content, condition)
    key, source, url = _desired(model, generated)
    if current["asset_key"] == key and current["asset_id"] == source:
        return ()
    old_key = current["asset_key"]
    image["data-asset-key"] = key
    image["data-asset-id"] = source
    image["src"] = url
    image["data-transformation-target-id"] = "asset:" + key
    target = _targeted(condition)["transformation_target_id"]
    changes = [
        {
            "transformation_target_id": "asset:" + key,
            "operation": "rewrite" if old_key == key else "add",
            "value": {
                "asset_key": key,
                "asset_id": source,
                "url": url,
                "kind": "ordinary_image",
                "alt": image.get("alt", ""),
                "parent_target_id": target,
                "position": 0,
                "html": str(image),
            },
        }
    ]
    condition_change = rewrite(
        _targeted(condition), "condition", condition.get("title", "Условие"), str(soup)
    )
    condition_change["value"]["asset_keys"] = [key]
    changes.append(condition_change)
    if old_key != key:
        changes.append(
            {"transformation_target_id": "asset:" + old_key, "operation": "remove"}
        )
    return tuple(changes)
