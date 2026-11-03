"""Prepare the two-height area method with a geometry-correct condition figure."""

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...probability import solution_diagrams as diagrams
from ...probability.common import line
from ..isosceles.planner import RepairPlan, _section
from ..isosceles.side_altitude_figures import _identity, condition_changes
from ..isosceles.side_altitude_proofs import number
from ..right.altitude_methods import solution_section
from ..right.altitude_parent import exact_answer
from ..right.basic_parent import _targeted
from .area_sources import HEIGHTS, review_parent, source_bytes
from .height_area_model import read_question
from .height_area_svg import height_svg

KEY = "height_area_condition"


def selection(context):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 two-height content is required")
    assets = content.get("assets")
    if (
        not isinstance(assets, list)
        or len(assets) != 1
        or not isinstance(assets[0], dict)
    ):
        raise ContentPlanError("one reviewed two-height condition image is required")
    asset = assets[0]
    key, identifier = asset.get("asset_key"), asset.get("asset_id")
    if (
        key not in {"image_1", KEY}
        or not isinstance(identifier, str)
        or not identifier
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != "/assets/" + identifier
        or (key == "image_1" and identifier != HEIGHTS)
    ):
        raise ContentPlanError("the two-height image metadata changed")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete two-height condition is required")
    soup = BeautifulSoup(condition["html"], "html.parser")
    images = soup.find_all("img")
    if (
        len(images) != 1
        or images[0].get("data-asset-key") != key
        or images[0].get("data-asset-id") != identifier
    ):
        raise ContentPlanError("the two-height image reference changed")
    images[0]["data-asset-key"] = "image_1"
    model = read_question(str(soup), identifier)
    raw = source_bytes(HEIGHTS)
    diagram = (
        None if model.native_compatible else diagrams.spec(KEY, height_svg(model, raw))
    )
    return model, asset, condition, diagram


def diagram_specs(context):
    diagram = selection(context)[-1]
    return (diagram,) if diagram else ()


def render(m):
    return solution_section(
        "Решение",
        "<p>Выразим площадь треугольника двумя способами — через каждую сторону и проведенную к ней высоту:</p>"
        + line(r"S_{ABC}=\frac{1}{2}CH\cdot AB")
        + line(r"S_{ABC}=\frac{1}{2}AK\cdot CB")
        + "<p>Приравняем выражения площади, сократим общий множитель 1/2 и найдем вторую высоту:</p>"
        + line(r"\frac{1}{2}CH\cdot AB=\frac{1}{2}AK\cdot CB")
        + line(r"CH\cdot AB=AK\cdot CB")
        + line(r"AK=\frac{CH\cdot AB}{CB}")
        + line(
            r"AK=\frac{"
            + number(m.h)
            + r"\cdot "
            + number(m.a)
            + "}{"
            + number(m.b)
            + "}"
        )
        + line(r"AK=\frac{" + number(m.h * m.a) + "}{" + number(m.b) + "}")
        + line("AK=" + number(m.answer)),
    )


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    generated_solution_assets=(),
):
    review_parent(parent_solution_html, "27623")
    if parent_condition_asset_id != HEIGHTS or parent_solution_assets:
        raise ContentPlanError("the reviewed two-height parent images changed")
    m, asset, condition, diagram = selection(context)
    key = KEY if diagram else "image_1"
    identifier, url = _identity(key, HEIGHTS, diagram, generated_solution_assets)
    changes = condition_changes(context, condition, asset, key, identifier, url)
    content = context["normalized_content"]
    plan = diagrams.repair(
        condition,
        _targeted(_section(content, "answer")),
        _targeted(_section(content, "solution")),
        exact_answer(m.answer),
        render(m),
        asset_changes=changes,
    )
    return RepairPlan(plan.answer, plan.transformations)
