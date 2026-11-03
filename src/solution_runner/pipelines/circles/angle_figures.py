"""Keep exact compatible circle diagrams and rebuild the two numbered arcs."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity, condition_changes
from .angle_model import read_question
from .angle_svg import SOURCE, figure_svg
from .quantity_sources import source_bytes

KEY = "circle_two_arcs"
LEGACY_RATIO_DETAIL = "efe00e1f-ac2e-450b-aa7d-166764145c7b"
SOURCES = {
    "cyclic_opposite": ("b2848d10-0706-4113-b70b-fee6abd8eb06",),
    "triangle_arc_ratio": (
        "93bf921d-8eb2-48ae-ac48-10b377c66641",
        "02f4ca89-190b-489e-8a40-02295b1a6991",
    ),
    "cyclic_four_arcs": ("b2848d10-0706-4113-b70b-fee6abd8eb06",),
    "cyclic_arc_ratio": ("b2848d10-0706-4113-b70b-fee6abd8eb06",),
    "cyclic_sum": (
        "81716d48-eee4-4e17-884b-3ef8bedd9276",
        "fe7c367d-af9e-4cfd-8626-cf65c3c64ac2",
    ),
    "cyclic_difference": ("5cbeeb21-d482-4558-8370-cf2fa3dea811",),
    "cyclic_largest": (
        "a581e5c7-5ae0-4d79-83a1-c70ea8452116",
        "fd4a0e7f-e14a-49f6-a218-c19216826aed",
    ),
    "central_difference": ("515f640e-4cd6-40ee-94b4-d171ac58f6ad",),
    "difference_equation": ("e37b7d86-ef1d-473b-8ef1-2777aefff55d",),
    "fraction": (
        "40ccd98b-48c9-469c-b30c-bbd010257d7c",
        "e5fc5324-bed5-42ef-a335-d244924dfe9a",
        "3a014817-745a-4049-8437-07d8337f8f20",
    ),
    "two_arcs": (
        SOURCE,
        "45075378-fe37-4226-87bf-d90d9275317e",
        "8aee4b45-3b33-4f1b-b6c3-236cf0eeb1f1",
    ),
    "diameters_central": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        "5be3c78f-0682-4cce-a623-1e7ff255692c",
    ),
    "diameters_inscribed": (
        "1f80d796-67fd-4b3b-9edc-e038caf927ee",
        "5be3c78f-0682-4cce-a623-1e7ff255692c",
    ),
    "secants": ("f98a097b-c129-44ea-b49b-059bde4c8963",),
}


def selection(context):
    content, assets, owners = read_content(context, {"image_1", "image_2", KEY})
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete circle-angle condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one circle-angle picture is supported")
    if images:
        images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), images[0]["data-asset-id"] if images else None)
    legacy = assets.pop("image_2", None)
    if legacy is not None:
        if (
            model.mode != "triangle_arc_ratio"
            or legacy["asset_id"] != LEGACY_RATIO_DETAIL
            or owners["image_2"] != "solution"
        ):
            raise ContentPlanError("the extra ratio diagram belongs to another method")
        source_bytes(LEGACY_RATIO_DETAIL)
    if len(assets) > 1:
        raise ContentPlanError("duplicate circle-angle pictures")
    for key, asset in assets.items():
        if key == KEY:
            if model.mode != "two_arcs" or owners[key] != "condition":
                raise ContentPlanError(
                    "a generated circle belongs to the numbered arc condition"
                )
        elif asset["asset_id"] not in SOURCES[model.mode]:
            raise ContentPlanError("the circle picture depicts another reviewed method")
        if model.mode != "two_arcs" and owners[key] != (
            "solution" if model.mode == "central_difference" else "condition"
        ):
            raise ContentPlanError("the circle picture belongs in another section")
    for source in SOURCES[model.mode]:
        source_bytes(source)
    drawing = spec(KEY, figure_svg(model)) if model.mode == "two_arcs" else None
    return model, condition, next(iter(assets.values()), {}), drawing


def diagram_specs(context):
    drawing = selection(context)[-1]
    return (drawing,) if drawing else ()


def prepare(context, generated):
    model, condition, current, drawing = selection(context)
    source = (
        current.get("asset_id", SOURCES[model.mode][0]) if drawing is None else SOURCE
    )
    key = KEY if drawing else "image_1"
    identifier, url = _identity(key, source, drawing, generated)
    if model.mode == "central_difference":
        image, changes = _attach(current or None, key, identifier, url, "solution")
        return model, changes, {"reference": "<center>" + image + "</center>"}, (key,)
    return (
        model,
        condition_changes(context, condition, current, key, identifier, url),
        {},
        (),
    )
