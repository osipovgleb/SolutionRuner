"""Evaluate C p(x-h) - p(Cx) for an affine function p."""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_EXPRESSION = re.compile(r"^(?P<c>\d+)p\(x(?P<sign>[+-])(?P<h>\d+)\)-p\((?P=c)x\)$")
_FUNCTION = re.compile(r"^p\(x\)=(?P<m>-?\d*)x(?P<d>[+-]\d+)$")


def _signed(value: int) -> str:
    return f"{value:+d}"


def _x_term(coefficient: int) -> str:
    if coefficient == 1:
        return "x"
    if coefficient == -1:
        return "-x"
    return f"{coefficient}x"


def _scaled_parentheses(coefficient: int, expression: str) -> str:
    if coefficient == 1:
        return f"({expression})"
    if coefficient == -1:
        return f"-({expression})"
    return f"{coefficient}\\cdot({expression})"


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets"):
        raise RightTrianglePlanError("text-only condition required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = [str(node.get("data-inline-latex") or "").replace(" ", "") for node in soup.find_all("span", attrs={"data-inline-latex": True})]
    if len(formulas) != 2:
        raise RightTrianglePlanError("condition must contain expression and function")
    expression = _EXPRESSION.fullmatch(formulas[0])
    function = _FUNCTION.fullmatch(formulas[1])
    if not expression or not function:
        raise RightTrianglePlanError("condition does not match scaled affine difference")

    coefficient, magnitude = int(expression["c"]), int(expression["h"])
    shift = magnitude if expression["sign"] == "+" else -magnitude
    shifted_argument = f"x{expression['sign']}{magnitude}"
    slope_text = function["m"]
    slope = -1 if slope_text == "-" else int(slope_text or "1")
    intercept = int(function["d"])
    first_argument, second_argument = 1 + shift, coefficient
    first_value = slope * first_argument + intercept
    second_value = slope * second_argument + intercept
    answer = coefficient * first_value - second_value
    first_formula = f"p({shifted_argument})={_scaled_parentheses(slope, shifted_argument)}{_signed(intercept)}"
    second_formula = f"p({coefficient}x)={_x_term(slope * coefficient)}{_signed(intercept)}"
    first_expanded = f"{_x_term(slope)}{_signed(slope * shift)}{_signed(intercept)}"
    second_expanded = f"{_x_term(slope * coefficient)}{_signed(intercept)}"
    substituted = (
        f"{formulas[0]}={_scaled_parentheses(coefficient, first_expanded)}"
        f"-({second_expanded})"
    )
    opened = (
        f"{substituted}={_x_term(coefficient * slope)}{_signed(coefficient * slope * shift)}"
        f"{_signed(coefficient * intercept)}{_x_term(-slope * coefficient)}{_signed(-intercept)}"
    )
    collected = f"{_x_term(coefficient * slope)}{_signed(coefficient * slope * shift)}{_signed(coefficient * intercept)}{_x_term(-slope * coefficient)}{_signed(-intercept)}={answer}"
    alternative = f"{coefficient}p({first_argument})-p({second_argument})"

    html = (
        '<p>Найдём значения функции:</p>'
        f'<center><p><span data-inline-latex="{first_formula}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="{second_formula}"></span>.</p></center>'
        '<p>Подставим найденные выражения в условие:</p>'
        f'<center><p><span data-inline-latex="{substituted}"></span>.</p></center>'
        '<p>Раскроем внутренние скобки:</p>'
        f'<center><p><span data-inline-latex="{opened}"></span>.</p></center>'
        '<p>Сложим подобные слагаемые:</p>'
        f'<center><p><span data-inline-latex="{collected}"></span>.</p></center>'
        '<p><b>Приведём другое решение</b></p>'
        '<p>Так как это задание первой части, переменная <span data-inline-latex="x"></span> в ответе быть не может, значит, она должна сократиться.</p>'
        '<p>Подставим <span data-inline-latex="x=1"></span>:</p>'
        f'<center><p><span data-inline-latex="{alternative}"></span>.</p></center>'
        '<p>Найдём значения функции:</p>'
        f'<center><p><span data-inline-latex="p({first_argument})={_scaled_parentheses(slope, str(first_argument))}{_signed(intercept)}={first_value}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="p({second_argument})={_scaled_parentheses(slope, str(second_argument))}{_signed(intercept)}={second_value}"></span>.</p></center>'
        '<p>Подставим найденные значения:</p>'
        f'<center><p><span data-inline-latex="{alternative}={coefficient}\\cdot({first_value})-({second_value})={answer}"></span>.</p></center>'
    ).replace("+-", "-")

    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    transformations = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        transformations.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != str(answer):
        transformations.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer}</span></p>'))
    return RepairPlan(answer=str(answer), transformations=tuple(transformations))
