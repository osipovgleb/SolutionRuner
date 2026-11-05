"""Reuse exact compatible solids and restore the parent's condition/solution roles."""

from functools import partial

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity
from .distance_figures import _condition_change
from .polyhedron_model import read_question
from .polyhedron_sources import SOLIDS, STYLES, source_bytes
from .polyhedron_svg import figure_svg

CONDITION = "box_polyhedron_condition"
SOLUTION = "box_polyhedron_solution"


def selection(context, *, rule):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", CONDITION, SOLUTION}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete polyhedron condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one polyhedron condition figure is supported")
    source = images[0].get("data-asset-id") if images else None
    if images:
        images[0]["data-asset-key"] = "image_1"
        images[0]["data-transformation-target-id"] = "asset:image_1"
    m = read_question(str(soup), source, preferred_axis=STYLES[rule]["preferred_axis"])
    for key, asset in assets.items():
        if key in {"image_1", "image_2"}:
            if asset["asset_id"] not in SOLIDS:
                raise ContentPlanError("the polyhedron figure needs review")
            source_bytes(asset["asset_id"])
        expected = "condition" if key in {"image_1", CONDITION} else "solution"
        legacy_solution = (
            key == "image_1"
            and owners[key] == "solution"
            and SOLIDS[asset["asset_id"]] is not None
        )
        if owners[key] != expected and not legacy_solution:
            raise ContentPlanError("the polyhedron figure has an unreviewed owner")
    figures = []
    for role, kind, base in STYLES[rule]["roles"]:
        current = [a for k, a in assets.items() if owners[k] == role]
        if len(current) > 1:
            raise ContentPlanError("duplicate polyhedron figures have the same role")
        old = current[0] if current else None
        expected = None if kind == "frame" else m.solid.vertices
        candidates = (
            ([old["asset_id"]] if old and old["asset_id"] in SOLIDS else [])
            + [a["asset_id"] for a in assets.values() if a["asset_id"] in SOLIDS]
            + [base]
            + list(SOLIDS)
        )
        source = next((s for s in candidates if SOLIDS[s] == expected), None)
        key = (
            ("image_1" if role == "condition" else "image_2")
            if source
            else CONDITION
            if role == "condition"
            else SOLUTION
        )
        drawing = None if source else spec(key, figure_svg(m, base))
        figures.append((role, old, source or base, key, drawing))
    return m, condition, assets, owners, figures


def diagram_specs(context, *, rule):
    return tuple(f[-1] for f in selection(context, rule=rule)[-1] if f[-1])


central_specs = partial(diagram_specs, rule="solid-polyhedron-central-tetrahedron")
prism_specs = partial(diagram_specs, rule="solid-polyhedron-half-box")
note_specs = partial(diagram_specs, rule="solid-polyhedron-pyramid-with-note")
triangle_specs = partial(diagram_specs, rule="solid-polyhedron-triangle-pyramid")
face_specs = partial(diagram_specs, rule="solid-polyhedron-face-pyramid")


def prepare(context, generated, *, rule):
    m, condition, assets, owners, figures = selection(context, rule=rule)
    expected = {f[3] for f in figures if f[4]}
    if (
        len(generated) != len(expected)
        or {a.get("asset_key") for a in generated} != expected
    ):
        raise ContentPlanError(
            "the prepared polyhedron figures differ from the actual vertices"
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
        current = assets.get(key)
        same_role = current if owners.get(key) == role else None
        image, attached = _attach(same_role, key, identifier, url, role)
        if current and owners.get(key) != role:
            for change in attached:
                if change["transformation_target_id"] == "asset:" + key:
                    change["operation"] = "rewrite"
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
