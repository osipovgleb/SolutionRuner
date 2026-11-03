"""Validate the reviewed rhombus sources and retain solution-figure ownership."""

from ...core.errors import ContentPlanError
from ...probability.solution_diagrams import spec
from ...triangles.isosceles.side_altitude_figures import _identity
from .bisector_svg import RHOMBUS_KEY, RHOMBUS_SOURCE, figure_svg
from .midpoint_figures import _attach
from .quantity_sources import source_bytes

RHOMBUS_SOURCES = {
    RHOMBUS_SOURCE,
    "58569964-9541-49bf-98c6-dc1df50de6e5",
    "bc0a45e8-c5d6-4e95-a26e-1e7d9319cfde",
    "acabb4d9-d90f-47b7-9be2-6ac1e4434b81",
    "3a54f85a-51d1-45d9-aed0-9a3cd92e0088",
}


def selection(model, condition, assets, owners):
    if len(assets) > 1:
        raise ContentPlanError("one rhombus solution figure is required")
    for key, asset in assets.items():
        if owners[key] != "solution" or key not in {"image_1", RHOMBUS_KEY}:
            raise ContentPlanError(
                "the rhombus figure belongs to another method or section"
            )
        if key == "image_1":
            if asset["asset_id"] not in RHOMBUS_SOURCES:
                raise ContentPlanError("the rhombus angle source needs a review")
            source_bytes(asset["asset_id"])
    diagram = spec(RHOMBUS_KEY, figure_svg(model))
    return model, condition, assets, RHOMBUS_SOURCE, diagram


def prepare(model, assets, diagram, generated):
    identifier, url = _identity(RHOMBUS_KEY, RHOMBUS_SOURCE, diagram, generated)
    current = next(iter(assets.values()), None)
    image, changes = _attach(current, RHOMBUS_KEY, identifier, url, "solution")
    return (
        model,
        tuple(changes),
        {"reference": "<center>" + image + "</center>"},
        (RHOMBUS_KEY,),
    )
