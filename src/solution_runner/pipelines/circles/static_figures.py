"""Validate and reuse reviewed static circle pictures in their exact section roles."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .quantity_sources import source_bytes


def selection(context, reader, sources, details, aliases):
    keys = {"image_1"} | {
        "image_" + str(i + 2) for row in details.values() for i in range(len(row))
    }
    content, assets, owners = read_content(context, keys)
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete static-circle condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one static-circle condition image is supported")
    model = reader(str(soup), images[0]["data-asset-id"] if images else None)
    expected = {"image_1": sources[model.mode]}
    for i, (_, source) in enumerate(details.get(model.mode, ())):
        expected["image_" + str(i + 2)] = (source, *aliases.get(source, ()))
    for key, asset in assets.items():
        if (
            key not in expected
            or asset["asset_id"] not in expected[key]
            or owners[key] != ("condition" if key == "image_1" else "solution")
        ):
            raise ContentPlanError(
                "the static-circle image depicts another method or section"
            )
        source_bytes(asset["asset_id"])
    for source in (
        *sources[model.mode],
        *(source for _, source in details.get(model.mode, ())),
    ):
        source_bytes(source)
    return model, condition, assets


def prepare(context, generated, reader, sources, details, aliases):
    model, condition, assets = selection(context, reader, sources, details, aliases)
    if generated:
        raise ContentPlanError(
            "compatible static circle pictures need no generated copies"
        )
    current = assets.get("image_1", {})
    source = current.get("asset_id", sources[model.mode][0])
    changes = list(
        condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
    )
    pictures, keys = {}, []
    if model.mode in details:
        changes = [
            t for t in changes if t["transformation_target_id"] != "asset:image_2"
        ]
    for i, (name, source) in enumerate(details.get(model.mode, ())):
        key = "image_" + str(i + 2)
        image, delta = _attach(
            assets.get(key), key, source, "/assets/" + source, "solution"
        )
        changes.extend(delta)
        pictures[name] = "<center>" + image + "</center>"
        keys.append(key)
    return model, tuple(changes), pictures, tuple(keys)
