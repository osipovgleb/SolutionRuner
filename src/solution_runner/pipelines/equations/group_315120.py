r"""Plans for logarithms of a power with a compatible integer base."""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, format_latex_fraction
from solution_runner.pipelines.equations.group_26646 import _section, _solution_signature
from solution_runner.pipelines.equations.group_26650 import _parse_linear, _rewrite
from solution_runner.pipelines.equations.group_26656 import RepairPlan

RULE = "logarithm-315120-power-argument-common-base"
_INTEGER_BASE = r"(?:[2-9]|[1-9]\d+)"
_FORMULA = re.compile(
    rf"\\log_(?P<base>\{{?\(?{_INTEGER_BASE}\)?\}}?)\s*(?P<argument_base>{_INTEGER_BASE})\^\{{(?P<exponent>[^{{}}]+)\}}=(?P<right>-?\d+)"
)
_PARENTHESIZED_BASE = re.compile(rf"\\log_\{{\((?P<base>{_INTEGER_BASE})\)\}}")


class UnsupportedCondition(ValueError):
    pass


def _base_degree(value: int, primitive: int) -> int:
    power = primitive
    degree = 1
    while power < value:
        power *= primitive
        degree += 1
    if power != value:
        raise UnsupportedCondition("logarithm base is not a power of the argument base")
    return degree


def _base_latex(value: int) -> str:
    return str(value) if value < 10 else f"{{{value}}}"


def _build_plan(formula: str) -> RepairPlan:
    match = _FORMULA.fullmatch(formula)
    if not match:
        raise UnsupportedCondition("unsupported logarithm of a power")
    base = int(match.group("base").strip("{}()"))
    argument_base = int(match.group("argument_base"))
    degree = _base_degree(base, argument_base)
    try:
        constant, coefficient = _parse_linear(match.group("exponent"))
    except ValueError as error:
        raise UnsupportedCondition("power exponent must be affine") from error
    if coefficient == 0:
        raise UnsupportedCondition("power exponent must contain x")
    right = int(match.group("right"))
    target = degree * right
    result = Fraction(target - constant, coefficient)
    try:
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("answer does not terminate") from error
    exponent = match.group("exponent")
    base_latex = _base_latex(base)
    solution = (
        f'<center><p><span data-inline-latex="\\log_{base_latex} {argument_base}^{{{exponent}}}={right}'
        f'\\iff {argument_base}^{{{exponent}}}={base_latex}^{{{right}}}'
        f'\\iff {argument_base}^{{{exponent}}}={argument_base}^{{{target}}}'
        f'\\iff {exponent}={target}\\iff x={format_latex_fraction(result)}"></span>.</p></center>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def _normal_formula(formula: str) -> str:
    return _PARENTHESIZED_BASE.sub(lambda match: f"\\log_{_base_latex(int(match.group('base')))}", formula)


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = context.get("normalized_content") or {}
    condition = _section(content, "condition")
    if not condition:
        raise UnsupportedCondition("missing condition")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(spans) != 1:
        raise UnsupportedCondition("condition must have one logarithmic formula")
    original = str(spans[0].get("data-inline-latex") or "")
    normalized = _normal_formula(original)
    plan = _build_plan(re.sub(r"\s+", "", normalized))
    answer_section, solution_section = _section(content, "answer"), _section(content, "solution")
    transformations: list[dict[str, Any]] = []
    if normalized != original:
        spans[0]["data-inline-latex"] = normalized
        transformations.append(_rewrite(condition, "condition", "Условие", str(soup)))
    if not solution_section or _solution_signature(str(solution_section.get("html") or "")) != _solution_signature(plan.solution_html):
        transformations.append(_rewrite(solution_section, "solution", "Решение", plan.solution_html))
    if not answer_section or BeautifulSoup(str(answer_section.get("html") or ""), "html.parser").get_text(" ", strip=True) != plan.answer:
        transformations.append(_rewrite(answer_section, "answer", "Ответ", f"<p>{plan.answer}</p>"))
    return RepairPlan(answer=plan.answer, condition_html="", solution_html=plan.solution_html, transformations=tuple(transformations))
