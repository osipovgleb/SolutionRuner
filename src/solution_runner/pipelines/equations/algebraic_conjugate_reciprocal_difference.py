"""Evaluate a(k²a²-b²)(1/(ka+b)-1/(ka-b))."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import _normalized_content, _section, _section_transformation
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


_EXPRESSION = re.compile(
    r"^a\((?P<square>\d+)a\^\{2\}-(?P<bsquare>\d+)\)\(\\frac\{1\}\{(?P<k>\d+)a\+(?P<b>\d+)\}-\\frac\{1\}\{(?P=k)a-(?P=b)\}\)$"
)
_VALUE = re.compile(r"^a=(?P<value>-?\d+(?:\{,\}\d+)?)$")
_TEXT_VALUE = re.compile(r"\ba\s*=\s*(?P<value>-?\d+(?:[,.]\d+)?)")


def _answer_text(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def _latex_decimal(text: str) -> str:
    return text.replace(",", "{,}")


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None or content.get("assets"):
        raise RightTrianglePlanError("text-only condition required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = [str(node.get("data-inline-latex") or "").replace(" ", "") for node in soup.find_all("span", attrs={"data-inline-latex": True})]
    if len(formulas) not in (1, 2):
        raise RightTrianglePlanError("condition must contain expression and value")
    expression = _EXPRESSION.fullmatch(formulas[0])
    value = _VALUE.fullmatch(formulas[1]) if len(formulas) == 2 else None
    if value is None and len(formulas) == 1:
        text_value = _TEXT_VALUE.search(soup.get_text(" ", strip=True).replace("\u00ad", ""))
        if text_value:
            value = _VALUE.fullmatch(f"a={text_value['value'].replace(',', '{,}')}")
    if not expression or not value:
        raise RightTrianglePlanError("condition does not match conjugate reciprocal difference")

    k, b = int(expression["k"]), int(expression["b"])
    if int(expression["square"]) != k * k or int(expression["bsquare"]) != b * b:
        raise RightTrianglePlanError("outer factor does not match the two denominators")
    value_latex = value["value"]
    value_decimal = Decimal(value_latex.replace("{,}", "."))
    coefficient = -2 * b
    answer = Decimal(coefficient) * value_decimal
    answer_text = _answer_text(answer)
    bracket = (
        f"\\frac{{1}}{{{k}a+{b}}}-\\frac{{1}}{{{k}a-{b}}}="
        f"\\frac{{{k}a-{b}-({k}a+{b})}}{{({k}a+{b})({k}a-{b})}}="
        f"-\\frac{{{2 * b}}}{{{k * k}a^{{2}}-{b * b}}}"
    )
    simplified = f"{formulas[0]}=a({k * k}a^{{2}}-{b * b})\\cdot\\left(-\\frac{{{2 * b}}}{{{k * k}a^{{2}}-{b * b}}}\\right)={coefficient}a"
    answer_latex = _latex_decimal(answer_text)
    html = (
        '<p>Приведём дроби в скобках к общему знаменателю:</p>'
        f'<center><p><span data-inline-latex="{bracket}"></span>.</p></center>'
        '<p>Сократим одинаковые множители:</p>'
        f'<center><p><span data-inline-latex="{simplified}"></span>.</p></center>'
        f'<p>Подставим <span data-inline-latex="a={value_latex}"></span>:</p>'
        f'<center><p><span data-inline-latex="{coefficient}\\cdot({value_latex})={answer_latex}"></span>.</p></center>'
    )
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    transformations = []
    if solution_section is None or str(solution_section.get("html") or "") != html:
        transformations.append(_section_transformation(solution_section, "solution", "Решение", html))
    current_answer = BeautifulSoup(str(answer_section.get("html") or "") if answer_section else "", "html.parser").get_text("", strip=True).replace(" ", "")
    if current_answer != answer_text:
        transformations.append(_section_transformation(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{answer_text}</span></p>'))
    return RepairPlan(answer=answer_text, transformations=tuple(transformations))
