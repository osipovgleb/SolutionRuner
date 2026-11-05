"""Reuse reviewed unnumbered box diagrams in their original condition role."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .box_model import read_question
from .box_sources import DIAGONAL_SOURCES, MODE_SOURCES, source_bytes


def selection(context):
    content, assets, owners = read_content(context, {"image_1"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete box condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("the reviewed box picture belongs in the condition")
    source = images[0].get("data-asset-id") if images else None
    model = read_question(condition["html"], source)
    current = assets.get("image_1", {})
    if current:
        if current["asset_id"] not in MODE_SOURCES[model.mode]:
            raise ContentPlanError("the box diagram depicts an unreviewed object")
        source_bytes(current["asset_id"])
        if (
            owners["image_1"] == "solution"
            and current["asset_id"] not in DIAGONAL_SOURCES
        ):
            raise ContentPlanError(
                "only the reviewed space-diagonal figure may move from the solution"
            )
    return model, condition, current


def prepare(context, condition, current, parent_source, generated):
    if generated:
        raise ContentPlanError("compatible box figures need no generated copies")
    source = current.get("asset_id", parent_source)
    source_bytes(source)
    return condition_changes(
        context, condition, current, "image_1", source, "/assets/" + source
    )
