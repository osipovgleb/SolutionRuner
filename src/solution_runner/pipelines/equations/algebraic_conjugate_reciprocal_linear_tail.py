"""Evaluate (k²b²-h²)(1/(kb-h)-1/(kb+h))+cb+d."""
from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_EXPRESSION = re.compile(
    r"^\((?P<square>\d+)b\^\{2\}-(?P<hsquare>\d+)\)\(\\frac\{1\}\{(?P<k>\d+)b-(?P<h>\d+)\}-\\frac\{1\}\{(?P=k)b\+(?P=h)\}\)(?P<c>[+-](?:\d+)?)b(?P<d>[+-]\d+)$"
)
_VALUE = re.compile(r"^b=(?P<value>-?\d+)$")


def _coefficient(text: str) -> int:
    return 1 if text == "+" else -1 if text == "-" else int(text)


def _linear_term(coefficient: int) -> str:
    if coefficient == 1:
        return "b"
    if coefficient == -1:
        return "-b"
    return f"{coefficient}b"


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
        raise RightTrianglePlanError("condition does not match conjugate reciprocal linear tail")
    k, h = int(expression["k"]), int(expression["h"])
    if int(expression["square"]) != k * k or int(expression["hsquare"]) != h * h:
        raise RightTrianglePlanError("outer factor does not match the denominators")
    coefficient, constant, b_value = _coefficient(expression["c"]), int(expression["d"]), int(value["value"])
    reduced_constant = 2 * h + constant
    answer = coefficient * b_value + reduced_constant
    bracket = (
        f"\\frac{{1}}{{{k}b-{h}}}-\\frac{{1}}{{{k}b+{h}}}="
        f"\\frac{{{k}b+{h}-({k}b-{h})}}{{({k}b-{h})({k}b+{h})}}="
        f"\\frac{{{2 * h}}}{{{k * k}b^{{2}}-{h * h}}}"
    )
    after_cancellation = f"{formulas[0]}={2 * h}{expression['c']}b{_signed(constant)}"
    reduced = f"{_linear_term(coefficient)}{_signed(reduced_constant)}"
    html = (
        '<p>Приведём дроби в скобках к общему знаменателю:</p>'
        f'<center><p><span data-inline-latex="{bracket}"></span>.</p></center>'
        '<p>Сократим одинаковые множители:</p>'
        f'<center><p><span data-inline-latex="{after_cancellation}={reduced}"></span>.</p></center>'
        f'<p>Подставим <span data-inline-latex="b={b_value}"></span>:</p>'
        f'<center><p><span data-inline-latex="{reduced}={coefficient}\\cdot({b_value}){_signed(reduced_constant)}={answer}"></span>.</p></center>'
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
