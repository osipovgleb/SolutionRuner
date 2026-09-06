"""Strict repair planner for equation group 77369."""
from __future__ import annotations
import re
from typing import Any
from bs4 import BeautifulSoup
from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError

RULE = "elementary-equations-77369-completed-square"
PARENT_PROBLEM_ID = "4041f11f-e39f-4e28-9978-51ea9dbe9b87"
_FORMULA = re.compile(r"\(x(?P<sign>[+-])(?P<value>[1-9]\d{0,5})\)\^\{2\}=(?P<right>-?[1-9]\d{0,6})x")

def build_repair_plan(context: dict[str, Any], *, parent_condition_asset_id: str | None, parent_solution_html: str = "", current_asset_content_type: str | None = None) -> RepairPlan:
    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id not in (None, ""):
        raise RightTrianglePlanError("group 77369 must not have a condition asset")
    content = _normalized_content(context)
    condition, answer_section, solution = (_section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("group 77369 condition is incomplete")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    if any(tag.name not in {"p", "span"} or (tag.name == "span" and set(tag.attrs) != {"data-inline-latex"}) or (tag.name == "p" and tag.attrs) for tag in soup.find_all(True)):
        raise RightTrianglePlanError("condition contains unsupported markup")
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text(strip=True):
        raise RightTrianglePlanError("equation markup is ambiguous")
    formula = str(spans[0].get("data-inline-latex") or "")
    match = _FORMULA.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError("condition does not match group 77369")
    s = int(match.group("value")) * (1 if match.group("sign") == "+" else -1)
    if int(match.group("right")) != 4 * s:
        raise RightTrianglePlanError("equation is not the audited completed-square form")
    s_text = str(s)
    expanded = f"x^{{2}}{2*s:+d}x+{s*s}={4*s}x".replace("+-", "-")
    moved = f"x^{{2}}{-2*s:+d}x+{s*s}=0".replace("+-", "-")
    square = f"(x{'-' if s >= 0 else '+'}{abs(s)})^{{2}}=0"
    expected_condition = f'<p>Ре­ши­те урав­не­ние <span data-inline-latex="{formula}"></span>.</p>'
    expected_solution = ('<p>Ис­поль­зу­ем фор­му­лы квад­ра­та суммы и раз­но­сти:</p><center><p><span> '
        f'<span data-inline-latex="{formula}\\iff {expanded}\\iff {moved}\\iff {square}\\iff x={s_text}"></span>.</span></p></center>')
    changes=[]
    if str(condition.get("html") or "") != expected_condition: changes.append(_section_transformation(condition,"condition","Условие",expected_condition))
    if solution is None or str(solution.get("html") or "") != expected_solution: changes.append(_section_transformation(solution,"solution","Решение",expected_solution))
    actual = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text(" ",strip=True)
    if actual != s_text: changes.append(_section_transformation(answer_section,"answer","Ответ",f'<p><span data-effect="spaced">{s_text}</span></p>'))
    return RepairPlan(answer=s_text, transformations=tuple(changes))
