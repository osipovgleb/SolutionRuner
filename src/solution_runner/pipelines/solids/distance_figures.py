"""Select exact compatible spatial sources or bind deterministic replacement SVGs."""

from bs4 import BeautifulSoup

from ..core.errors import ContentPlanError
from ..probability.solution_diagrams import spec
from ..quadrilaterals.parallelogram.midpoint_figures import _attach
from ..quadrilaterals.quantity_content import read_content
from ..triangles.isosceles.planner import _section
from ..triangles.isosceles.side_altitude_figures import _identity
from ..triangles.right.basic_parent import _targeted
from ..word_problems.common import rewrite
from . import distance_svg, spatial_distance_sources, spatial_distance_svg
from .box_condition_repairs import restore_html
from .box_distance_geometry import blue
from .distance_answer_figures import clean_context
from .distance_sources import FIGURES, MODE_SOURCES, source_bytes
from .spatial_distance_model import MODES, read_question

CONDITION = "box_distance_condition"
SOLUTION = "box_distance_solution"
ROLES = {
    "distance_squared": (
        ("condition", "image_1", "f4689cbc-e217-4787-85bf-30a406dc5ce7"),
        ("solution", "image_2", "626ee550-5e35-469c-b555-65cb5466e6ea"),
    ),
    "distance": (
        ("condition", "image_1", "6c17c081-08ea-43fa-9da5-5fb7a08387a2"),
        ("solution", "image_2", "66d11cfd-6c56-4268-8b85-6e4549417bbe"),
    ),
    "edge": (("condition", "image_1", "e8daeb88-d29f-4113-8de3-1bbe5e85bb48"),),
    "diagonal": (("solution", "image_1", "49dfc211-0bca-4ca2-8d18-27e2ed416906"),),
}


ROLES = ROLES | spatial_distance_sources.ROLES


def compatible(model, source, role, slot=None):
    if model.mode in MODES:
        return spatial_distance_sources.compatible(model, source, role, slot)
    data = FIGURES[source]
    required, allowed = blue(model, role)
    marked = {tuple(x) for x in data["blue"]}
    numeric = model.mode in {"distance", "distance_squared"}
    return (
        not numeric or data["dimensions"] == tuple(str(v) for v in model.squares)
    ) and set(required) <= marked <= set(allowed)


def _read(context):
    content, assets, owners = read_content(
        clean_context(context), {"image_1", "image_2", "image_3", CONDITION, SOLUTION}
    )
    condition = _section(content, "condition")
    if condition is None:
        raise ContentPlanError("one complete spatial box condition is required")
    restored = restore_html(condition["html"])
    soup = BeautifulSoup(restored, "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise ContentPlanError("one spatial condition figure is supported")
    source = images[0].get("data-asset-id") if images else None
    if images and images[0].get("data-asset-key") != "image_1":
        images[0]["data-asset-key"] = "image_1"
        images[0]["data-transformation-target-id"] = "asset:image_1"
    model = read_question(str(soup), source)
    for key, a in assets.items():
        allowed = (
            spatial_distance_sources.allowed_keys(model.mode)
            if model.mode in MODES
            else set()
        )
        if model.mode in spatial_distance_sources.GENERATED_MODES:
            allowed.add(SOLUTION)
        if key == "image_3" and key not in allowed:
            raise ContentPlanError("the third spatial diagram needs a reviewed method")
        if model.mode in MODES and (key not in allowed or owners[key] != "solution"):
            raise ContentPlanError(
                "the proof-only spatial diagrams belong to the solution"
            )
        expected = (
            "condition"
            if key == CONDITION
            or key == "image_1"
            and model.mode not in {"diagonal", *MODES}
            else "solution"
        )
        if (
            owners[key] != expected
            or model.mode == "diagonal"
            and key in {"image_2", CONDITION}
            or model.mode == "edge"
            and key == SOLUTION
        ):
            raise ContentPlanError(
                "the spatial figure has an unreviewed section or method role"
            )
        if key in {"image_1", "image_2", "image_3"}:
            if a["asset_id"] not in MODE_SOURCES[model.mode]:
                raise ContentPlanError("the spatial figure needs review")
            if model.mode in MODES and key not in spatial_distance_sources.slots(
                spatial_distance_sources.DATA["figures"][a["asset_id"]]
            ):
                raise ContentPlanError(
                    "the proof diagram occupies another reviewed slot"
                )
            source_bytes(a["asset_id"])
    return model, condition, restored, assets, owners


def selection(context):
    m, condition, restored, assets, owners = _read(context)
    m = spatial_distance_sources.reviewed_model(m, assets) if m.mode in MODES else m
    figures = []
    roles = spatial_distance_sources.roles(m) if m.mode in MODES else ROLES[m.mode]
    for role, native_key, base in roles:
        current = [
            a
            for k, a in assets.items()
            if owners[k] == role and not (m.mode == "edge" and role == "solution")
        ]
        if m.mode in MODES:
            current = [a for a in current if a["asset_key"] in {native_key, SOLUTION}]
        if len(current) > 1:
            raise ContentPlanError("duplicate spatial figures have the same role")
        old = current[0] if current else None
        candidates = (
            (
                [old["asset_id"]]
                if old
                and (
                    old["asset_id"] in FIGURES
                    or m.mode in MODES
                    and old["asset_id"] in MODE_SOURCES[m.mode]
                )
                else []
            )
            + [a["asset_id"] for a in assets.values() if a["asset_id"] in FIGURES]
            + [base]
            + list(MODE_SOURCES[m.mode])
        )
        source = next(
            (s for s in candidates if compatible(m, s, role, native_key)), None
        )
        key = native_key if source else CONDITION if role == "condition" else SOLUTION
        drawing = (
            None
            if source
            else spec(
                key,
                spatial_distance_svg.render(m)
                if m.mode in MODES
                else distance_svg.figure_svg(m, base, role),
            )
        )
        figures.append((role, old, source or base, key, drawing))
    return m, condition, restored, assets, figures


def diagram_specs(context):
    return tuple(f[-1] for f in selection(context)[-1] if f[-1])


def _condition_change(condition, restored, image, current, key, identifier):
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if (
        restored == condition["html"]
        and images
        and current
        and (current["asset_key"], current["asset_id"]) == (key, identifier)
    ):
        return ()
    soup = BeautifulSoup(restored, "html.parser")
    old = soup.find("img")
    new = BeautifulSoup(image, "html.parser").img
    if old:
        old.replace_with(new)
    elif soup.find("p"):
        soup.find("p").insert(0, new)
    else:
        soup.insert(0, new)
    change = rewrite(
        _targeted(condition), "condition", condition.get("title", "Условие"), str(soup)
    )
    change["value"]["asset_keys"] = [key]
    return (change,)


def prepare(context, generated):
    m, condition, restored, assets, figures = selection(context)
    expected = {f[3] for f in figures if f[4]}
    if (
        len(generated) != len(expected)
        or {g.get("asset_key") for g in generated} != expected
    ):
        raise ContentPlanError(
            "the prepared spatial figures differ from the actual geometry"
        )
    changes = []
    pictures = {}
    keys = []
    desired = set()
    for role, old, source, key, drawing in figures:
        if m.mode in MODES:
            m = spatial_distance_sources.with_symbols(m, source)
        identifier, url = _identity(
            key,
            source,
            drawing,
            tuple(g for g in generated if g.get("asset_key") == key),
        )
        image, attached = _attach(old, key, identifier, url, role)
        changes.extend(attached)
        desired.add(key)
        if role == "condition":
            changes.extend(
                _condition_change(condition, restored, image, old, key, identifier)
            )
        else:
            pictures[key if m.mode in MODES else "solution"] = image
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
    return (
        m,
        tuple(changes),
        pictures if m.mode in MODES else pictures.get("solution", ""),
        tuple(keys),
    )
