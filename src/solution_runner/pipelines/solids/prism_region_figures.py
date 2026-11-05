"""Retain reviewed body drawings and restore exact highlighted vertex subsets."""

from ..core.errors import ContentPlanError
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..triangles.isosceles.side_altitude_figures import condition_changes
from .prism_sources import DATA, source_bytes


def validate(m, assets, owners):
    if set(assets) - {"image_1", "image_2"}:
        raise ContentPlanError("the vertex-volume prism figure slot needs review")
    for key, a in assets.items():
        role = "condition" if key == "image_1" else "solution"
        f = DATA["figures"].get(a["asset_id"])
        if (
            not f
            or m.body not in f.get("region_bodies", [])
            or owners[key] != role
            or [key, role] not in f["slots"]
        ):
            raise ContentPlanError(
                "the vertex-volume prism figure has another body or role"
            )
        if role == "solution" and sorted(m.vertices) not in f.get("vertex_sets", []):
            raise ContentPlanError(
                "the highlighted prism vertices differ from the requested solid"
            )
        source_bytes(a["asset_id"])


def prepare(context, m, condition, assets, generated):
    if generated:
        raise ContentPlanError(
            "compatible native vertex-volume diagrams need no generated copies"
        )
    compatible = [
        s["source"]
        for s in DATA["region_scenes"]
        if s["body"] == m.body and s["vertices"] == sorted(m.vertices)
    ]
    if not compatible:
        raise ContentPlanError(
            "the highlighted prism vertex subset needs a reviewed diagram"
        )
    current = assets.get("image_1", {})
    source = current.get("asset_id", DATA["region_conditions"][m.body])
    changes = list(
        condition_changes(
            context,
            condition,
            current,
            "image_1",
            source,
            "/assets/" + source,
            preserve_assets=("image_2",),
        )
    )
    old = assets.get("image_2")
    source = old["asset_id"] if old else compatible[0]
    picture, attached = _attach(old, "image_2", source, "/assets/" + source, "solution")
    changes.extend(attached)
    return m, tuple(changes), {"image_2": picture}, ("image_2",)
