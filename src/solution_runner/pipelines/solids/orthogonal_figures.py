"""Retain each child's exact numerical drawing in its condition role."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from .orthogonal_reader import read
from .orthogonal_sources import RULES


def selection(context, rule):
    content, assets, owners = read_content(context, {"image_1"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete numeric solid condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) != 1 or len(assets) != 1 or owners != {"image_1": "condition"}:
        raise ContentPlanError(
            "the numerical solid requires its original condition drawing"
        )
    model, kind = read(condition["html"], images[0]["data-asset-id"])
    if RULES.get(rule) != kind:
        raise ContentPlanError(
            "the diagram differs from the parent's reviewed solid topology"
        )
    return model
