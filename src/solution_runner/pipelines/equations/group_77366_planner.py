"""Deterministic rational-equation root selector for source group 77366."""

from __future__ import annotations

import math
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError

RULE = "elementary-equations-77366-rational-square-root-selector"
_FORMULA = re.compile(r"\\frac\{(?P<numerator>\d+)\}\{x\^\{2\}(?P<sign>[+-])(?P<constant>\d+)\}=1")
_KIND = re.compile(r"в ответе запишите (?P<kind>больший|меньший) из корней\.?$")


def build_repair_plan(
    context: dict[str, Any], *, parent_condition_asset_id: str | None,
    parent_solution_html: str = "", current_asset_content_type: str | None = None,
) -> RepairPlan:
    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id not in (None, ""):
        raise RightTrianglePlanError("group 77366 must not have assets")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("condition is incomplete")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text(strip=True):
        raise RightTrianglePlanError("condition formula is ambiguous")
    formula = str(spans[0].get("data-inline-latex") or "")
    match = _FORMULA.fullmatch(formula)
    text = " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split())
    kind = _KIND.search(text)
    if not match or not kind:
        raise RightTrianglePlanError("condition does not match group 77366")
    numerator, constant = int(match.group("numerator")), int(match.group("constant"))
    sign = match.group("sign")
    square = numerator + constant if sign == "-" else numerator - constant
    root = math.isqrt(square)
    if root == 0 or root * root != square:
        raise RightTrianglePlanError("derived square is not a positive perfect square")
    answer_value = root if kind.group("kind") == "больший" else -root
    expected_solution = (
        "<p>По­сле­до­ва­тель­но по­лу­ча­ем:</p>"
        f'<center><p><span data-inline-latex="{formula}\\iff x^{{2}}{sign}{constant}={numerator}\\iff x^{{2}}={square}\\iff \\left[\\begin{{aligned}}x={root}\\\\x=-{root}\\end{{aligned}}\\right."></span>.</p></center>'
        f"<p>{'Боль­ший' if answer_value > 0 else 'Мень­ший'} ко­рень равен {answer_value}.</p>"
    )
    changes: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != expected_solution:
        changes.append(_section_transformation(solution, "solution", "Решение", expected_solution))
    current_answer = BeautifulSoup(str(answer.get("html") or "") if answer else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != str(answer_value):
        changes.append(_section_transformation(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{answer_value}</span></p>'))
    return RepairPlan(answer=str(answer_value), transformations=tuple(changes))
