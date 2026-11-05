"""Retain exact native roles and prepare only reviewed missing solution diagrams."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity
from .orthogonal_element_input import read as question
from .orthogonal_element_model import read
from .orthogonal_element_sources import DATA, source_bytes
from .orthogonal_element_svg import render

KEY = "orthogonal_element_solution"


def selection(context, method=None):
    content, assets, owners = read_content(context, {"image_1", "image_2", KEY})
    condition = _section(content, "condition")
    if condition is None or "image_1" not in assets or owners["image_1"] != "condition":
        raise ContentPlanError(
            "the complete own numerical condition drawing is required"
        )
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if (
        len(images) != 1
        or len(assets) > 2
        or any(role != "solution" for key, role in owners.items() if key != "image_1")
    ):
        raise ContentPlanError(
            "one original condition and one solution diagram are supported"
        )
    source = assets["image_1"]["asset_id"]
    mode, requested = question(condition["html"], source)
    review = DATA["proofs"].get(source + ":" + mode + ":" + requested)
    model = read(source, mode, requested, method or (review or {}).get("method"))
    native = review["solution_source"]
    if native:
        source_bytes(native)
        if (
            KEY in assets
            or "image_2" in assets
            and assets["image_2"]["asset_id"] != native
        ):
            raise ContentPlanError(
                "the existing solution drawing has different dimensions or helpers"
            )
        return model, assets, "image_2", native, None
    if "image_2" in assets:
        raise ContentPlanError(
            "the missing helper drawing cannot reuse an unreviewed parent image"
        )
    return model, assets, KEY, source, spec(KEY, render(source, model))


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def prepare(context, method, generated):
    model, assets, key, source, diagram = selection(context, method)
    identifier, url = _identity(key, source, diagram, generated)
    picture, changes = _attach(assets.get(key), key, identifier, url, "solution")
    return model, picture, (key,), tuple(changes)
