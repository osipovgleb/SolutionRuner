"""Reuse inside-center figures and prepare both outside-center diagram roles."""

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity, condition_changes
from .circumcircle_height_model import (
    CONDITION_KEY,
    DETAIL,
    DETAIL_KEY,
    INSIDE_SOURCES,
    SOURCE,
)
from .circumcircle_height_svg import figure_svg
from .quantity_sources import source_bytes


def selection(context, model):
    content, assets, owners = read_content(
        context, {"image_1", "image_2", CONDITION_KEY, DETAIL_KEY}
    )
    condition = _section(content, "condition")
    primary = [a for k, a in assets.items() if k in {"image_1", CONDITION_KEY}]
    detail = [a for k, a in assets.items() if k in {"image_2", DETAIL_KEY}]
    if len(primary) > 1 or len(detail) > 1:
        raise ContentPlanError("each trapezoid-height picture role must be unique")
    for key, asset in assets.items():
        role = "condition" if key in {"image_1", CONDITION_KEY} else "solution"
        expected = {"image_1": INSIDE_SOURCES, "image_2": (DETAIL,)}.get(key)
        if owners[key] != role or (
            expected is not None and asset["asset_id"] not in expected
        ):
            raise ContentPlanError(
                "the trapezoid-height picture depicts another method or section"
            )
    source_bytes(SOURCE)
    source_bytes(DETAIL)
    drawings = (
        ()
        if model.given[3]
        else (
            spec(CONDITION_KEY, figure_svg(model, False)),
            spec(DETAIL_KEY, figure_svg(model, True)),
        )
    )
    return (
        condition,
        primary[0] if primary else {},
        detail[0] if detail else {},
        drawings,
    )


def diagram_specs(context, model):
    return selection(context, model)[-1]


def prepare(context, model, generated):
    condition, primary, detail, drawings = selection(context, model)
    if not drawings and generated:
        raise ContentPlanError("compatible trapezoid pictures need no generated copies")
    if len(generated) != len(drawings) or {a.get("asset_key") for a in generated} != {
        d["asset_key"] for d in drawings
    }:
        raise ContentPlanError(
            "the prepared trapezoid-height diagrams differ from both selected roles"
        )
    keys = (CONDITION_KEY, DETAIL_KEY) if drawings else ("image_1", "image_2")
    identities = []
    for i, (key, source) in enumerate(zip(keys, (SOURCE, DETAIL))):
        if not drawings:
            current = primary if i == 0 else detail
            if current.get("asset_key") == key:
                source = current["asset_id"]
        drawing = drawings[i] if drawings else None
        identities.append(
            _identity(
                key,
                source,
                drawing,
                tuple(a for a in generated if a["asset_key"] == key),
            )
        )
    changes = [
        t
        for t in condition_changes(context, condition, primary, keys[0], *identities[0])
        if t["transformation_target_id"] != "asset:image_2"
    ]
    image, delta = _attach(detail or None, keys[1], *identities[1], "solution")
    return model, tuple(changes + delta), {"height": image}, (keys[1],)
