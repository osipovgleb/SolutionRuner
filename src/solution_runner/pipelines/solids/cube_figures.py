"""Validate full cube image roles and reuse every compatible source identity."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity, condition_changes
from . import cube_section_svg
from .cube_model import read_question
from .cube_sources import MODE_SOURCES, source_bytes


def selection(context):
    content, assets, owners = read_content(context, {"image_1", cube_section_svg.KEY})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete cube condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one cube condition image is supported")
    source = images[0].get("data-asset-id") if images else None
    m = read_question(condition["html"], source)
    if len(assets) > 1:
        raise ContentPlanError("one cube image role is supported")
    for key, a in assets.items():
        section = m.mode == "midpoint_section_angle"
        if (
            owners[key] != ("solution" if section else "condition")
            or key == cube_section_svg.KEY
            and not section
        ):
            raise ContentPlanError(
                "the cube image belongs to another section or method"
            )
        if key == "image_1":
            if a["asset_id"] not in MODE_SOURCES[m.mode]:
                raise ContentPlanError("the cube diagram depicts an unreviewed object")
            source_bytes(a["asset_id"])
    drawing = (
        spec(cube_section_svg.KEY, cube_section_svg.figure_svg(m))
        if m.mode == "midpoint_section_angle" and not cube_section_svg.compatible(m)
        else None
    )
    return m, condition, next(iter(assets.values()), {}), drawing


def model(context):
    return selection(context)[0]


def diagram_specs(context):
    drawing = selection(context)[-1]
    return (drawing,) if drawing else ()


def prepare(context, m, generated, parent_source):
    _, condition, current, drawing = selection(context)
    if m.mode != "midpoint_section_angle":
        if generated:
            raise ContentPlanError("compatible cube pictures need no generated copies")
        source = current.get("asset_id", parent_source)
        source_bytes(source)
        changes = condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
        return changes, {}, ()
    if drawing is None and generated:
        raise ContentPlanError(
            "the compatible corner section needs no generated copies"
        )
    key = cube_section_svg.KEY if drawing else "image_1"
    identifier, url = _identity(key, cube_section_svg.SOURCE, drawing, generated)
    image, changes = _attach(current or None, key, identifier, url, "solution")
    return tuple(changes), {"section": image}, (key,)
