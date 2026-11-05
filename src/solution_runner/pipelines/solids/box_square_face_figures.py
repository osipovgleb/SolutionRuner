"""Reuse the reviewed square-face projection across unnumbered acute-angle scenes."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from .box_model import read_question
from .box_sources import source_bytes
from .distance_figures import _condition_change

CONDITION = "08c7d343-8614-486e-9908-f1fecbfcc25a"
SOLUTION = "4a7ae0f0-49ed-4c45-8a86-4bad3555fe03"
SYMBOLIC = "0e694766-7a31-4a7d-8df0-cfd6d722e362"


def selection(context):
    content, assets, owners = read_content(context, {"image_1", "image_2"})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete square-face condition is required")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one square-face condition diagram is supported")
    m = read_question(
        condition["html"], images[0].get("data-asset-id") if images else None
    )
    if m.mode != "square_face_volume":
        raise ContentPlanError(
            "the parent method requires a square-face diagonal angle"
        )
    for key, asset in assets.items():
        allowed = (CONDITION,) if owners[key] == "condition" else (SOLUTION, SYMBOLIC)
        if (
            asset["asset_id"] not in allowed
            or key == "image_2"
            and owners[key] != "solution"
        ):
            raise ContentPlanError(
                "the square-face diagram has an unreviewed object or role"
            )
        source_bytes(asset["asset_id"])
    if any(list(owners.values()).count(role) > 1 for role in ("condition", "solution")):
        raise ContentPlanError("duplicate square-face diagrams have the same role")
    return m, condition, assets, owners


def prepare(context, generated):
    if generated:
        raise ContentPlanError(
            "compatible square-face diagrams need no generated copies"
        )
    m, condition, assets, owners = selection(context)
    old_solution = next((a for k, a in assets.items() if owners[k] == "solution"), None)
    changes, picture = [], ""
    for key, role, source in (
        ("image_1", "condition", CONDITION),
        ("image_2", "solution", old_solution["asset_id"] if old_solution else SOLUTION),
    ):
        source_bytes(source)
        old = assets.get(key) if owners.get(key) == role else None
        image, attached = _attach(old, key, source, "/assets/" + source, role)
        if key in assets and owners[key] != role:
            for change in attached:
                change["operation"] = "rewrite"
        changes.extend(attached)
        if role == "condition":
            changes.extend(
                _condition_change(condition, condition["html"], image, old, key, source)
            )
        else:
            picture = image
    return m, tuple(changes), picture, ("image_2",)
