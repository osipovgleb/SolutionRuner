"""Plans for ratios of powers whose literal factors cancel."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_FORMULA = re.compile(
    r"^\\frac\{\((?P<first>\d+)a\^\{2\}\)\^\{3\}\\cdot"
    r"\((?P<second>\d+)b\)\^\{2\}\}"
    r"\{\((?P<product>\d+)a\^\{3\}b\)\^\{2\}\}$"
)


def _formula(condition: dict[str, Any]) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(formulas) != 1:
        raise RightTrianglePlanError("condition must contain one formula")
    return str(formulas[0].get("data-inline-latex") or "").replace(" ", "")


def _solution_html(primary: str, alternative: str) -> str:
    """Keep only the body; the runtime supplies the solution-section wrapper."""

    return (
        f'<p><span data-inline-latex="{primary}"></span>.</p>'
        '<p><b>Приведем другое решение</b></p>'
        '<p>Так как это задание первой части, переменных '
        '<span data-inline-latex="a"></span> и <span data-inline-latex="b"></span> '
        'в ответе быть не может, значит, они должны сократиться. '
        'Поэтому подставим <span data-inline-latex="a=b=1"></span>: '
        f'<span data-inline-latex="{alternative}"></span>.</p>'
    )


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build both the parent-style expansion and the unit-substitution method."""

    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    if condition is None or content.get("assets") or tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("power-cancellation conditions must be text-only")
    formula = _formula(condition)
    match = _FORMULA.fullmatch(formula)
    if match is None:
        raise RightTrianglePlanError("condition does not match the registered power-cancellation form")
    first, second, product = (int(match[name]) for name in ("first", "second", "product"))
    if first * second != product:
        raise RightTrianglePlanError("numeric denominator does not match the factors")

    primary = (
        f"{formula}=\\frac{{{first}^{{3}}a^{{6}}\\cdot{second}^{{2}}b^{{2}}}}"
        f"{{{product}^{{2}}a^{{6}}b^{{2}}}}="
        f"\\frac{{{first}^{{3}}\\cdot{second}^{{2}}}}"
        f"{{{first}^{{2}}\\cdot{second}^{{2}}}}={first}"
    )
    alternative = (
        f"\\frac{{({first}\\cdot1^{{2}})^{{3}}\\cdot({second}\\cdot1)^{{2}}}}"
        f"{{({product}\\cdot1^{{3}}\\cdot1)^{{2}}}}="
        f"\\frac{{{first}^{{3}}\\cdot{second}^{{2}}}}{{{product}^{{2}}}}="
        f"\\frac{{{first}^{{3}}\\cdot{second}^{{2}}}}"
        f"{{{first}^{{2}}\\cdot{second}^{{2}}}}={first}"
    )
    answer = str(first)
    html = _solution_html(primary, alternative)
    changes: list[dict[str, Any]] = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        changes.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != answer:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'
        ))
    return RepairPlan(answer=answer, transformations=tuple(changes))
