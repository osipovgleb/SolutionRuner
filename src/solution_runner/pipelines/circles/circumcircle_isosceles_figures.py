"""Reuse compatible diagrams and replace inside-center pictures for obtuse inputs."""

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity, condition_changes
from .circumcircle_isosceles_content import validation_context
from .circumcircle_isosceles_model import (
    CONDITION_KEY,
    DETAIL,
    DETAIL_KEY,
    OBTUSE,
    SOURCE,
    kind,
)
from .circumcircle_isosceles_svg import figure_svg
from .quantity_sources import source_bytes


def selection(context, model, reader):
    clean = validation_context(context, reader)
    content, assets, owners = read_content(
        clean, {"image_1", "image_2", CONDITION_KEY, DETAIL_KEY}
    )
    primary = [a for k, a in assets.items() if k in {"image_1", CONDITION_KEY}]
    detail = [a for k, a in assets.items() if k in {"image_2", DETAIL_KEY}]
    if len(primary) > 1 or len(detail) > 1:
        raise ContentPlanError("each isosceles figure role must be unique")
    for key, asset in assets.items():
        expected = {"image_1": (SOURCE, OBTUSE), "image_2": (DETAIL,)}.get(key)
        if (
            owners[key]
            != ("condition" if key in {"image_1", CONDITION_KEY} else "solution")
            or expected is not None
            and asset["asset_id"] not in expected
        ):
            raise ContentPlanError(
                "the isosceles figure depicts another method or section"
            )
    for source in (SOURCE, OBTUSE, DETAIL):
        source_bytes(source)
    shape = kind(model)
    drawings = []
    if shape == "right":
        drawings.append(spec(CONDITION_KEY, figure_svg(model, False)))
    if shape != "acute":
        drawings.append(spec(DETAIL_KEY, figure_svg(model, True)))
    return (
        _section(content, "condition"),
        primary[0] if primary else {},
        detail[0] if detail else {},
        tuple(drawings),
    )


def diagram_specs(context, model, reader):
    return selection(context, model, reader)[-1]


def prepare(context, model, generated, reader):
    condition, primary, detail, drawings = selection(context, model, reader)
    if not drawings and generated:
        raise ContentPlanError("compatible isosceles pictures need no generated copies")
    if len(generated) != len(drawings) or {a.get("asset_key") for a in generated} != {
        d["asset_key"] for d in drawings
    }:
        raise ContentPlanError(
            "the prepared isosceles pictures differ from the selected geometry"
        )
    shape = kind(model)
    primary_key = CONDITION_KEY if shape == "right" else "image_1"
    detail_key = "image_2" if shape == "acute" else DETAIL_KEY
    identities = []
    for key, source in [
        (primary_key, OBTUSE if shape == "obtuse" else SOURCE),
        (detail_key, DETAIL),
    ]:
        drawing = next((d for d in drawings if d["asset_key"] == key), None)
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
        for t in condition_changes(
            context, condition, primary, primary_key, *identities[0]
        )
        if t["transformation_target_id"] != "asset:image_2"
    ]
    image, delta = _attach(detail or None, detail_key, *identities[1], "solution")
    return model, tuple(changes + delta), {"center": image}, (detail_key,)
