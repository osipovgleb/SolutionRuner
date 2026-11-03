"""Keep the polygon in the first solution section; reuse the native pentagon."""

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.side_altitude_figures import _identity
from .circumcircle_polygon_svg import SOURCE, figure_svg
from .quantity_sources import source_bytes

KEY = "circumcircle_regular_polygon"


def selection(context, model):
    _, assets, owners = read_content(context, {"image_1", KEY})
    if len(assets) > 1 or any(owner != "solution" for owner in owners.values()):
        raise ContentPlanError("one regular-polygon solution picture is supported")
    current = next(iter(assets.values()), {})
    if current.get("asset_key") == "image_1" and current["asset_id"] != SOURCE:
        raise ContentPlanError("the native polygon solution picture needs review")
    source_bytes(SOURCE)
    drawing = spec(KEY, figure_svg(model)) if model.answer != 5 else None
    return current, drawing


def diagram_specs(context, model):
    _, drawing = selection(context, model)
    return (drawing,) if drawing else ()


def prepare(context, model, generated):
    current, drawing = selection(context, model)
    if drawing is None and generated:
        raise ContentPlanError("the compatible pentagon needs no generated copies")
    key = KEY if drawing else "image_1"
    identifier, url = _identity(key, SOURCE, drawing, generated)
    image, changes = _attach(current or None, key, identifier, url, "solution")
    return model, tuple(changes), {"polygon": "<p>" + image + "</p>"}, (key,)
