"""Retain native prism figure roles and restore only reviewed compatible method diagrams."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import condition_changes
from . import prism_metric_figures, prism_region_figures
from .prism_metric_model import KINDS as METRIC_KINDS
from .prism_model import read_question
from .prism_region import KIND as REGION_KIND
from .prism_sources import DEFAULTS, RULES, compatible
from .prism_water_input import correction


def selection(context, *, rule=None):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", prism_metric_figures.KEY}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete prism condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one native prism condition drawing is supported")
    m = read_question(
        condition["html"], images[0].get("data-asset-id") if images else None
    )
    if rule is not None and m.kind not in RULES[rule]:
        raise ContentPlanError(
            "the complete prism question differs from its reviewed methods"
        )
    if m.kind == REGION_KIND:
        prism_region_figures.validate(m, assets, owners)
        return m, condition, assets, owners
    if m.kind in METRIC_KINDS:
        prism_metric_figures.validate(m, assets, owners)
        return m, condition, assets, owners
    if set(assets) - set(DEFAULTS[m.kind]):
        raise ContentPlanError("the prism figure slot needs review")
    for key, a in assets.items():
        compatible(m, key, a["asset_id"], owners[key])
    return m, condition, assets, owners


def prepare(context, generated, *, rule):
    m, condition, assets, owners = selection(context, rule=rule)
    if m.kind == REGION_KIND:
        return prism_region_figures.prepare(context, m, condition, assets, generated)
    if m.kind in METRIC_KINDS:
        return prism_metric_figures.prepare(
            context, m, condition, assets, owners, generated
        )
    if generated:
        raise ContentPlanError("reviewed prism drawings need no generated copies")
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
    if m.kind == "immersion":
        changes.extend(correction(condition))
    return m, tuple(changes), pictures, tuple(keys)


def diagram_specs(context):
    m, _condition, assets, owners = selection(context)
    if m.kind not in METRIC_KINDS:
        return ()
    drawing = prism_metric_figures.choice(m, assets, owners)[1]
    return (drawing,) if drawing else ()
