"""Keep compatible K diagrams and relabel reviewed spatial symmetries when necessary."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity
from .box_midpoint_model import read_question
from .box_midpoint_sources import FIGURES, source_bytes
from .box_midpoint_svg import CONDITION, SOLUTION, compatible, figure_svg
from .distance_figures import _condition_change

KEYS = {"condition": "box_midpoint_condition", "solution": "box_midpoint_solution"}


def selection(context):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", *KEYS.values()}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete midpoint section condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one midpoint condition picture is supported")
    if images:
        images[0]["data-asset-key"] = "image_1"
        images[0]["data-transformation-target-id"] = "asset:image_1"
    m = read_question(str(soup), images[0].get("data-asset-id") if images else None)
    for key, a in assets.items():
        if key in {"image_1", "image_2"}:
            source_bytes(a["asset_id"])
            if FIGURES[a["asset_id"]][0] != owners[key]:
                raise ContentPlanError("the midpoint picture has an unreviewed role")
        elif key != KEYS[owners[key]]:
            raise ContentPlanError("the generated midpoint picture has another role")
    if any(list(owners.values()).count(role) > 1 for role in KEYS):
        raise ContentPlanError("duplicate midpoint pictures have the same role")
    has_condition = "condition" in owners.values()
    if has_condition and owners.get("image_1") == "solution":
        raise ContentPlanError(
            "the reviewed two-picture layout uses image_1 for the condition"
        )
    figures = []
    for role, base in (("condition", CONDITION), ("solution", SOLUTION)):
        old = next((a for k, a in assets.items() if owners[k] == role), None)
        if role == "condition" and old is None:
            continue
        candidates = (
            [old["asset_id"]] if old and old["asset_id"] in FIGURES else []
        ) + list(FIGURES)
        source = next((s for s in candidates if compatible(m, s, role)), None)
        native_key = (
            "image_1"
            if role == "condition"
            or not has_condition
            and (not old or old["asset_key"] != "image_2")
            else "image_2"
        )
        key = native_key if source else KEYS[role]
        drawing = None if source else spec(key, figure_svg(m, base))
        figures.append((role, old, source or base, key, drawing))
    return m, condition, figures


def diagram_specs(context):
    return tuple(f[-1] for f in selection(context)[-1] if f[-1])


def prepare(context, generated):
    m, condition, figures = selection(context)
    expected = {f[3] for f in figures if f[4]}
    if (
        len(generated) != len(expected)
        or {g.get("asset_key") for g in generated} != expected
    ):
        raise ContentPlanError(
            "the prepared midpoint figures differ from the actual plane"
        )
    changes = []
    picture = ""
    keys = []
    for role, old, source, key, drawing in figures:
        identifier, url = _identity(
            key,
            source,
            drawing,
            tuple(g for g in generated if g.get("asset_key") == key),
        )
        image, attached = _attach(old, key, identifier, url, role)
        changes.extend(attached)
        if role == "condition":
            changes.extend(
                _condition_change(
                    condition, condition["html"], image, old, key, identifier
                )
            )
        else:
            picture = image
            keys.append(key)
    return m, tuple(changes), picture, tuple(keys)
