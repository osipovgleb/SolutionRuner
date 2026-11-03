"""Prepare exact rectangle methods and restore compatible existing condition SVGs."""

from html import escape

from bs4 import BeautifulSoup

from ...core.errors import ContentPlanError
from ...triangles.isosceles.planner import RepairPlan, _section
from ...triangles.isosceles.side_altitude_figures import condition_changes
from ...triangles.right.basic_parent import _targeted
from ...word_problems.common import rewrite
from .rectangle_model import RULES, read_question
from .rectangle_proofs import render, value
from .rectangle_sources import review_parent


def _condition(context, source):
    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("schema_version") != 3
        or content.get("format") != "teacherhelper-normalized"
    ):
        raise ContentPlanError("schema-v3 normalized rectangle content is required")
    sections, assets = content.get("sections"), content.get("assets")
    if not isinstance(sections, list) or any(not isinstance(s, dict) for s in sections):
        raise ContentPlanError("complete rectangle sections are required")
    if (
        not isinstance(assets, list)
        or any(not isinstance(a, dict) for a in assets)
        or len(assets) > 1
    ):
        raise ContentPlanError("one complete rectangle condition figure is supported")
    condition = _section(content, "condition")
    if condition is None or not isinstance(condition.get("html"), str):
        raise ContentPlanError("one complete rectangle condition is required")
    for section in sections:
        if section is not condition and (
            section.get("asset_keys")
            or BeautifulSoup(str(section.get("html") or ""), "html.parser").find("img")
        ):
            raise ContentPlanError(
                "these rectangle methods have only a condition figure"
            )
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    if (
        len(images) != len(assets)
        or len(images) > 1
        or condition.get("asset_keys", []) != (["image_1"] if images else [])
    ):
        raise ContentPlanError("rectangle image references differ from metadata")
    if assets:
        a = assets[0]
        if (
            a.get("asset_key") != "image_1"
            or a.get("asset_id") != source
            or a.get("kind") != "ordinary_image"
            or a.get("url") != "/assets/" + source
        ):
            raise ContentPlanError("the rectangle condition source is unreviewed")
    return content, condition, assets[0] if assets else {}


def prepare(
    context,
    *,
    parent_condition_asset_id,
    parent_solution_html,
    parent_solution_assets=(),
    content_rule_key,
):
    source = parent_condition_asset_id
    review_parent(
        content_rule_key, source, parent_solution_html, parent_solution_assets
    )
    content, condition, current = _condition(context, source)
    model = read_question(condition["html"], source)
    if RULES[content_rule_key] != model.mode:
        raise ContentPlanError("the complete rectangle question differs from its rule")
    changes = list(
        condition_changes(
            context, condition, current, "image_1", source, "/assets/" + source
        )
    )
    html = render(model)
    solution = _targeted(_section(content, "solution"))
    if solution is None or solution.get("html") != html:
        change = rewrite(solution, "solution", "Решение", html)
        change["value"]["asset_keys"] = []
        changes.append(change)
    answer = value(model.answer).replace("{,}", ",")
    if "\\" in answer:
        markup = (
            '<p><span data-inline-latex="'
            + escape(answer, quote=True)
            + '"></span></p>'
        )
    else:
        markup = f'<p><span data-effect="spaced">{answer}</span></p>'
    current_answer = _targeted(_section(content, "answer"))
    if current_answer is None or current_answer.get("html") != markup:
        change = rewrite(current_answer, "answer", "Ответ", markup)
        change["value"]["asset_keys"] = []
        changes.append(change)
    return RepairPlan(answer, tuple(changes))
