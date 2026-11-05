"""Reuse compatible cone diagrams, retaining each child's existing condition or solution role."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .cone_model import read_question
from .cone_sources import BASIC, PARENTS, compatible


def selection(context, *, rule):
    content, assets, owners = read_content(context, {"image_1"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete cone condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one cone condition diagram is supported")
    m = read_question(
        condition["html"], images[0].get("data-asset-id") if images else None
    )
    current = assets.get("image_1", {})
    role = (
        owners["image_1"]
        if current
        else "solution"
        if PARENTS[rule][1]
        else "condition"
    )
    if (
        role not in {"condition", "solution"}
        or role == "solution"
        and (m.mode != "geometry" or current and current["asset_id"] not in BASIC)
    ):
        raise ContentPlanError("the cone drawing has an unreviewed section role")
    compatible(m, current.get("asset_id", PARENTS[rule][0]))
    return m, condition, current, role


def prepare(context, generated, *, rule):
    if generated:
        raise ContentPlanError("reviewed cone figures need no generated copies")
    m, condition, current, role = selection(context, rule=rule)
    source = current.get("asset_id", PARENTS[rule][0])
    if role == "condition":
        changes = condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
        return m, changes, "", ()
    image, changes = _attach(
        current or None, "image_1", source, "/assets/" + source, "solution"
    )
    return m, tuple(changes), image, ("image_1",)
