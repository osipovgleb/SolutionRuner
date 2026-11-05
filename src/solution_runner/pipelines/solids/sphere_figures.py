"""Reuse exact one/two-sphere diagrams in the parent's condition role."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .sphere_model import read_question
from .sphere_sources import MODE_SOURCES, source_bytes


def selection(context):
    content, assets, owners = read_content(context, {"image_1"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete sphere condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1 or any(role != "condition" for role in owners.values()):
        raise ContentPlanError("the reviewed sphere picture belongs in the condition")
    current = assets.get("image_1", {})
    m = read_question(
        condition["html"], images[0].get("data-asset-id") if images else None
    )
    mode = (
        m.mode
        if m.mode != "combined_radius"
        else "combined_radius_" + ("volume" if m.degree == 3 else "area")
    )
    if current:
        if current["asset_id"] not in MODE_SOURCES[mode]:
            raise ContentPlanError(
                "the sphere diagram depicts another object or number of spheres"
            )
        source_bytes(current["asset_id"])
    return m, mode, condition, current


def prepare(context, generated):
    if generated:
        raise ContentPlanError("reviewed sphere diagrams need no generated copies")
    m, mode, condition, current = selection(context)
    if not MODE_SOURCES[mode]:
        return m, mode, ()
    source = current.get("asset_id", MODE_SOURCES[mode][0])
    source_bytes(source)
    return (
        m,
        mode,
        condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        ),
    )
