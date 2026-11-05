"""Reuse exact cylinder diagrams in their reviewed condition or solution role."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .cylinder_model import read_question
from .cylinder_sources import MODE_SOURCES, PARENTS, source_bytes


def selection(context, *, rule):
    content, assets, owners = read_content(context, {"image_1"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete cylinder condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one cylinder condition picture is supported")
    m = read_question(
        condition["html"], images[0].get("data-asset-id") if images else None
    )
    primary, solution_assets, _ = PARENTS[rule]
    role = None if primary is None else "solution" if solution_assets else "condition"
    current = assets.get("image_1", {})
    if current:
        if owners["image_1"] != role or current["asset_id"] not in MODE_SOURCES[m.mode]:
            raise ContentPlanError(
                "the cylinder figure depicts another object or has an unreviewed role"
            )
        source_bytes(current["asset_id"])
    return m, condition, current, role


def prepare(context, generated, *, rule):
    if generated:
        raise ContentPlanError("reviewed cylinder figures need no generated copies")
    m, condition, current, role = selection(context, rule=rule)
    if role is None:
        return m, (), "", ()
    source = current.get("asset_id", PARENTS[rule][0])
    source_bytes(source)
    if role == "condition":
        changes = condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
        return m, changes, "", ()
    image, changes = _attach(
        current or None, "image_1", source, "/assets/" + source, "solution"
    )
    return m, tuple(changes), image, ("image_1",)
