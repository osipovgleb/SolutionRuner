"""Reuse reviewed angle triangles and replace only incompatible numbers or segments."""

import re

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity
from .box_coordinates import VERTEX
from .box_vertex_angle_model import read_question, segments
from .distance_figures import _condition_change
from .vertex_angle_sources import FIGURES, MEMBERS, source_bytes
from .vertex_angle_svg import figure_svg

CONDITION = "box_vertex_angle_condition"
SOLUTION = "box_vertex_angle_solution"
RULES = {
    "solid-box-angle-from-face-diagonal": True,
    "solid-box-angle-from-base-diagonal": False,
}
BASE = {
    True: (
        ("condition", "50bc8b3b-c24f-48f2-bb1c-1a41f4f46e63"),
        ("solution", "8b1e6c2a-fdbe-4d22-bd94-89ef488e18f2"),
    ),
    False: (("condition", "c6f82a07-d4e0-4232-a4ad-5fcb3ba5590b"),),
}


def angle_key(requested):
    a, b, c = re.findall(VERTEX, requested)
    return b, tuple(sorted((a, c)))


def compatible(m, source, role):
    data = FIGURES[source]
    return (
        data["role"] == role
        and (
            data["dimensions"] is None
            or tuple(data["dimensions"]) == tuple(str(v) for v in m.squares)
        )
        and tuple(data["helpers"])
        == (() if role == "condition" and not data["helpers"] else segments(m))
        and (
            data["angle"] is None or angle_key(data["angle"]) == angle_key(m.requested)
        )
    )


def selection(context, *, with_solution):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", CONDITION, SOLUTION}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete box angle condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one box angle condition figure is supported")
    source = images[0].get("data-asset-id") if images else None
    if images:
        images[0]["data-asset-key"] = "image_1"
        images[0]["data-transformation-target-id"] = "asset:image_1"
    m = read_question(str(soup), source)
    rule = next(k for k, v in RULES.items() if v == with_solution)
    for key, a in assets.items():
        role = "condition" if key in {"image_1", CONDITION} else "solution"
        if owners[key] != role or not with_solution and role == "solution":
            raise ContentPlanError("the angle figure differs from its parent role")
        if key in {"image_1", "image_2"}:
            if a["asset_id"] not in MEMBERS[rule]:
                raise ContentPlanError("the angle figure needs review")
            source_bytes(a["asset_id"])
    figures = []
    for role, base in BASE[with_solution]:
        current = [a for k, a in assets.items() if owners[k] == role]
        if len(current) > 1:
            raise ContentPlanError("duplicate figures have the same angle role")
        old = current[0] if current else None
        candidates = (
            ([old["asset_id"]] if old and old["asset_id"] in FIGURES else [])
            + [base]
            + [
                s
                for s in MEMBERS[rule]
                if FIGURES[base]["dimensions"] is None
                or FIGURES[s]["dimensions"] is not None
            ]
        )
        source = next((s for s in candidates if compatible(m, s, role)), None)
        key = (
            ("image_1" if role == "condition" else "image_2")
            if source
            else CONDITION
            if role == "condition"
            else SOLUTION
        )
        drawing = (
            None if source else spec(key, figure_svg(m, base, mark=role == "condition"))
        )
        figures.append((role, old, source or base, key, drawing))
    return m, condition, assets, figures


def condition_specs(context):
    return tuple(f[-1] for f in selection(context, with_solution=False)[-1] if f[-1])


def solution_specs(context):
    return tuple(f[-1] for f in selection(context, with_solution=True)[-1] if f[-1])


def prepare(context, generated, *, with_solution):
    m, condition, assets, figures = selection(context, with_solution=with_solution)
    expected = {f[3] for f in figures if f[4]}
    if (
        len(generated) != len(expected)
        or {a.get("asset_key") for a in generated} != expected
    ):
        raise ContentPlanError(
            "the prepared angle figures differ from the actual triangle"
        )
    changes = []
    picture = ""
    keys = []
    desired = set()
    for role, old, source, key, drawing in figures:
        identifier, url = _identity(
            key,
            source,
            drawing,
            tuple(a for a in generated if a.get("asset_key") == key),
        )
        image, attached = _attach(old, key, identifier, url, role)
        changes.extend(attached)
        desired.add(key)
        if role == "condition":
            changes.extend(
                _condition_change(
                    condition, condition["html"], image, old, key, identifier
                )
            )
        else:
            picture = image
            keys.append(key)
    for key in set(assets) - desired:
        if not any(
            t["transformation_target_id"] == "asset:" + key
            and t["operation"] == "remove"
            for t in changes
        ):
            changes.append(
                {"transformation_target_id": "asset:" + key, "operation": "remove"}
            )
    return m, tuple(changes), picture, tuple(keys)
