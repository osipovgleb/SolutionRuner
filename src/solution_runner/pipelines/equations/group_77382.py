r"""Fail-closed plans for ``log_(affine x)(perfect power)=integer``."""

from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import (
    NumberFormatError,
    format_answer,
    format_latex_fraction,
)
from solution_runner.pipelines.equations.group_26646 import (
    _section,
    _solution_signature,
)
from solution_runner.pipelines.equations.group_26650 import _parse_linear, _rewrite
from solution_runner.pipelines.equations.group_26656 import RepairPlan

from .equation_conditions import read_equation_prompt

RULE = "logarithm-77382-affine-base-perfect-power"
_FORMULA = re.compile(
    r"\\log_\{?\(?(?P<base>-?\d+[+-]\d*x|-?\d*x(?:[+-]\d+)?)\)?\}?"
    r"\s*(?P<argument>[1-9]\d*)=(?P<power>[2-9]\d*)"
)


class UnsupportedCondition(ValueError):
    pass


def _integer_nth_root(value: int, degree: int) -> int:
    root = round(value ** (1 / degree))
    for candidate in range(max(1, root - 2), root + 3):
        if candidate**degree == value:
            return candidate
    raise UnsupportedCondition("logarithm argument is not an exact power")


def _build_plan(formula: str) -> RepairPlan:
    match = _FORMULA.fullmatch(formula)
    if not match:
        raise UnsupportedCondition("unsupported variable-base logarithm")
    base = match.group("base")
    try:
        constant, coefficient = _parse_linear(base)
    except ValueError as error:
        raise UnsupportedCondition("logarithm base must be affine") from error
    if coefficient == 0:
        raise UnsupportedCondition("logarithm base must contain x")
    argument, power = int(match.group("argument")), int(match.group("power"))
    root = _integer_nth_root(argument, power)
    result = Fraction(root - constant, coefficient)
    if constant + coefficient * result != root or root <= 0 or root == 1:
        raise UnsupportedCondition("derived logarithm base is invalid")
    try:
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("answer does not terminate") from error
    base_roots = f"\\pm {root}" if power % 2 == 0 else str(root)
    final = f"x={format_latex_fraction(result)}"
    if base != "x":
        final = f"{base}={root}\\iff {final}"
    solution = (
        "<p>По определению логарифма перейдём к уравнению на его основание. "
        "Основание должно быть положительным и не равным единице:</p>"
        f'<center><p><span data-inline-latex="{formula}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="\\begin{{cases}}{argument}=({base})^{{{power}}}\\\\{base}\\gt 0\\\\{base}\\ne 1\\end{{cases}}"></span>.</p></center>'
        "<p>Из найденных значений основания оставим только допустимые:</p>"
        f'<center><p><span data-inline-latex="\\begin{{cases}}{base}={base_roots}\\\\{base}\\gt 0\\\\{base}\\ne 1\\end{{cases}}"></span>.</p></center>'
        f'<center><p><span data-inline-latex="{final}"></span>.</p></center>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = context.get("normalized_content") or {}
    if (
        content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
        or content.get("assets")
    ):
        raise UnsupportedCondition(
            "schema-v3 normalized content without assets is required"
        )
    condition = _section(content, "condition")
    if not condition or condition.get("asset_keys"):
        raise UnsupportedCondition("missing condition")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span")
    if (
        len(spans) != 1
        or spans[0].get_text(strip=True)
        or set(spans[0].attrs) != {"data-inline-latex"}
    ):
        raise UnsupportedCondition("condition must have one logarithmic formula")
    formula = read_equation_prompt(
        str(condition.get("html") or ""),
        allow_selector=True,
        error_type=UnsupportedCondition,
    )
    plan = _build_plan(re.sub(r"\s+", "", formula))
    answer_section, solution_section = (
        _section(content, "answer"),
        _section(content, "solution"),
    )
    transformations: list[dict[str, Any]] = []
    if not solution_section or _solution_signature(
        str(solution_section.get("html") or "")
    ) != _solution_signature(plan.solution_html):
        transformations.append(
            _rewrite(solution_section, "solution", "Решение", plan.solution_html)
        )
    if (
        not answer_section
        or BeautifulSoup(str(answer_section.get("html") or ""), "html.parser").get_text(
            " ", strip=True
        )
        != plan.answer
    ):
        transformations.append(
            _rewrite(answer_section, "answer", "Ответ", f"<p>{plan.answer}</p>")
        )
    return RepairPlan(
        answer=plan.answer,
        condition_html="",
        solution_html=plan.solution_html,
        transformations=tuple(transformations),
    )
