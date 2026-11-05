"""Prepare the reviewed parallel-line sine method and compatible box figures."""

import hashlib
import json
from importlib.resources import files

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..quadrilaterals.quantity_repair import repair_quantity
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity
from . import box_svg, line_angle_proof
from .box_line_angle_model import read_question, segments
from .line_angle_sources import SOURCE, review_parent, source_bytes

KEY = "box_line_angle_solution"
TEMPLATE_SHA = "c6cf019598a34004f148890bc961aa9720e1b4b401f90263474812dbe89d46f7"
NATIVE_SEGMENTS = (("A", "C"), ("A_1", "C_1"))


def selection(context):
    content, assets, owners = read_content(context, {"image_1", KEY})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete box line-angle condition is required")
    m = read_question(condition["html"])
    if len(assets) > 1 or any(owner != "solution" for owner in owners.values()):
        raise ContentPlanError("one box line-angle solution figure is supported")
    old = next(iter(assets.values()), None)
    if old and old["asset_key"] == "image_1" and old["asset_id"] != SOURCE:
        raise ContentPlanError("the box line-angle figure needs review")
    raw = source_bytes()
    drawing = None
    if segments(m) != NATIVE_SEGMENTS:
        meta = (
            files(__package__)
            .joinpath("assets/box-line-angle-template.json")
            .read_bytes()
        )
        if hashlib.sha256(meta).hexdigest() != TEMPLATE_SHA:
            raise ContentPlanError("the reviewed line-angle template changed")
        svg = box_svg.render_svg(raw, json.loads(meta)[SOURCE], m.squares, segments(m))
        drawing = spec(KEY, svg)
    return m, old, drawing


def diagram_specs(context):
    drawing = selection(context)[-1]
    return (drawing,) if drawing else ()


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
    content_rule_key,
):
    review_parent(
        content_rule_key,
        parent_condition_asset_id,
        parent_solution_html,
        parent_solution_assets,
    )
    m, old, drawing = selection(context)
    if len(generated_solution_assets) != bool(drawing):
        raise ContentPlanError(
            "the prepared box line-angle figure differs from the geometry"
        )
    key = KEY if drawing else "image_1"
    identifier, url = _identity(key, SOURCE, drawing, generated_solution_assets)
    picture, changes = _attach(old, key, identifier, url, "solution")
    return repair_quantity(
        context, m.answer, line_angle_proof.render(m, picture), (key,), tuple(changes)
    )
