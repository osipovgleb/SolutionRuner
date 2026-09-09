"""Evaluate p(x-a) + p(b-x) for an affine function p."""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_EXPRESSION = re.compile(r"^p\(x-(?P<a>\d+)\)\+p\((?P<b>\d+)-x\)$")
_FUNCTION = re.compile(r"^p\(x\)=(?P<m>-?\d*)x(?P<d>[+-]\d+)$")


def _linear(value: int, slope: int, intercept: int) -> int:
    return slope * value + intercept


def _signed(value: int) -> str:
    return f"{value:+d}"


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets"):
        raise RightTrianglePlanError("text-only condition required")

    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = [
        str(node.get("data-inline-latex") or "").replace(" ", "")
        for node in soup.find_all("span", attrs={"data-inline-latex": True})
    ]
    if len(formulas) != 2:
        raise RightTrianglePlanError("condition must contain expression and function")

    expression = _EXPRESSION.fullmatch(formulas[0])
    function = _FUNCTION.fullmatch(formulas[1])
    if not expression or not function:
        raise RightTrianglePlanError("condition does not match complementary affine sum")

    a, b = int(expression["a"]), int(expression["b"])
    slope_text = function["m"]
    slope = -1 if slope_text == "-" else int(slope_text or "1")
    intercept = int(function["d"])
    first_argument, second_argument = 1 - a, b - 1
    first_value = _linear(first_argument, slope, intercept)
    second_value = _linear(second_argument, slope, intercept)
    answer = first_value + second_value

    first_substitution = f"p(x-{a})={slope}\\cdot(x-{a}){_signed(intercept)}"
    second_substitution = f"p({b}-x)={slope}\\cdot({b}-x){_signed(intercept)}"
    opened = (
        f"p(x-{a})+p({b}-x)="
        f"{slope}x{_signed(-slope * a)}{_signed(intercept)}"
        f"+{slope * b}{_signed(-slope)}x{_signed(intercept)}"
    )
    collected = f"{slope * (b - a)}{_signed(2 * intercept)}={answer}"
    alternative_expression = f"p({first_argument})+p({second_argument})"

    html = (
        '<p>Подставим аргументы в формулу, задающую функцию:</p>'
        f'<center><p><span data-inline-latex="{first_substitution}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="{second_substitution}"></span>.</p></center>'
        '<p>Раскроем скобки:</p>'
        f'<center><p><span data-inline-latex="{opened}"></span>.</p></center>'
        '<p>Сложим подобные слагаемые:</p>'
        f'<center><p><span data-inline-latex="{collected}"></span>.</p></center>'
        '<p><b>Приведём другое решение</b></p>'
        '<p>Так как это задание первой части, переменная <span data-inline-latex="x"></span> в ответе быть не может, значит, она должна сократиться.</p>'
        '<p>Подставим <span data-inline-latex="x=1"></span>:</p>'
        f'<center><p><span data-inline-latex="{alternative_expression}"></span>.</p></center>'
        '<p>Найдём значения функции:</p>'
        f'<center><p><span data-inline-latex="p({first_argument})={slope}\\cdot({first_argument}){_signed(intercept)}={first_value}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="p({second_argument})={slope}\\cdot({second_argument}){_signed(intercept)}={second_value}"></span>.</p></center>'
        '<p>Подставим найденные значения:</p>'
        f'<center><p><span data-inline-latex="{alternative_expression}={first_value}{_signed(second_value)}={answer}"></span>.</p></center>'
    ).replace("+-", "-")

    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    transformations = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        transformations.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(
        str(answer_section.get("html") or "") if answer_section else "", "html.parser"
    ).get_text("", strip=True).replace(" ", "")
    if current_answer != str(answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=str(answer), transformations=tuple(transformations))
