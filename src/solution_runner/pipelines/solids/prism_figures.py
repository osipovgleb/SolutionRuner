"""Retain native prism figure roles and restore only reviewed compatible method diagrams."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .prism_model import read_question
from .prism_sources import DEFAULTS, RULES, compatible


def selection(context, *, rule):
    content, assets, owners = read_content(context, {"image_1", "image_2"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete prism condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one native prism condition drawing is supported")
    m = read_question(
        condition["html"], images[0].get("data-asset-id") if images else None
    )
    if m.kind not in RULES[rule]:
        raise ContentPlanError(
            "the complete prism question differs from its reviewed methods"
        )
    if set(assets) - set(DEFAULTS[m.kind]):
        raise ContentPlanError("the prism figure slot needs review")
    for key, a in assets.items():
        compatible(m, key, a["asset_id"], owners[key])
    return m, condition, assets, owners


def prepare(context, generated, *, rule):
    if generated:
        raise ContentPlanError("reviewed prism drawings need no generated copies")
    m, condition, assets, owners = selection(context, rule=rule)
    changes = []
    pictures = {}
    keys = []
    for key, (default_role, default_source) in DEFAULTS[m.kind].items():
        current = assets.get(key, {})
        source = current.get("asset_id", default_source)
        role = owners.get(key, default_role)
        compatible(m, key, source, role)
        if role == "condition":
            changes.extend(
                condition_changes(
                    context,
                    condition,
                    current,
                    key,
                    source,
                    "/assets/" + source,
                    preserve_assets=tuple(DEFAULTS[m.kind]),
                )
            )
        else:
            image, attached = _attach(
                current or None, key, source, "/assets/" + source, "solution"
            )
            changes.extend(attached)
            pictures[key] = image
            keys.append(key)
    return m, tuple(changes), pictures, tuple(keys)
