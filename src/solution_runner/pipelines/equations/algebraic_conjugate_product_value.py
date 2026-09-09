"""Evaluate (ax-b)(ax+b)-a²x²+cx+d at an integer x."""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_EXPRESSION = re.compile(
    r"^\((?P<a>\d+)x-(?P<b>\d+)\)\((?P=a)x\+(?P=b)\)-(?P<square>\d+)x\^\{2\}(?:(?P<c>[+-](?:\d+)?)x)?(?P<d>[+-]\d+)?$"
)
_VALUE = re.compile(r"^x=(?P<x>-?\d+)$")


def _signed(value: int) -> str:
    return f"{value:+d}"


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets"):
        raise RightTrianglePlanError("text-only condition required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = [str(node.get("data-inline-latex") or "").replace(" ", "") for node in soup.find_all("span", attrs={"data-inline-latex": True})]
    if len(formulas) != 2:
        raise RightTrianglePlanError("condition must contain expression and value")
    expression = _EXPRESSION.fullmatch(formulas[0])
    value = _VALUE.fullmatch(formulas[1])
    if not expression or not value:
        raise RightTrianglePlanError("condition does not match conjugate product value")

    a, b, square = int(expression["a"]), int(expression["b"]), int(expression["square"])
    coefficient_text = expression["c"]
    coefficient = 1 if coefficient_text == "+" else -1 if coefficient_text == "-" else int(coefficient_text or "0")
    constant = int(expression["d"] or "0")
    x_value = int(value["x"])
    if square != a * a:
        raise RightTrianglePlanError("square coefficient does not match the conjugate factors")
    reduced_constant = constant - b * b
    answer = coefficient * x_value + reduced_constant
    expanded = f"{square}x^{{2}}-{b * b}-{square}x^{{2}}{_signed(coefficient)}x{_signed(constant)}"
    reduced = f"{coefficient}x{_signed(reduced_constant)}" if coefficient else str(reduced_constant)

    html = (
        '<p>Используем формулу разности квадратов:</p>'
        '<center><p><span data-inline-latex="a^{2}-b^{2}=(a-b)(a+b)"></span>.</p></center>'
        '<p>Преобразуем выражение:</p>'
        f'<center><p><span data-inline-latex="{formulas[0]}={expanded}={reduced}"></span>.</p></center>'
        f'<p>Подставим <span data-inline-latex="x={x_value}"></span>:</p>'
        f'<center><p><span data-inline-latex="{reduced}={coefficient}\\cdot({x_value}){_signed(reduced_constant)}={answer}"></span>.</p></center>' if coefficient else
        f'<center><p><span data-inline-latex="{reduced}={answer}"></span>.</p></center>'
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
