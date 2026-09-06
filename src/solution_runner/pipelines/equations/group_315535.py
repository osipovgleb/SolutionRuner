r"""Plans for ``a^(log_b(affine x)) = c`` when ``b`` is a power of ``a``."""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, format_latex_fraction
from solution_runner.pipelines.equations.group_26646 import _section, _solution_signature
from solution_runner.pipelines.equations.group_26650 import _linear_latex, _parse_linear, _rewrite
from solution_runner.pipelines.equations.group_26656 import RepairPlan

RULE = "logarithm-315535-exponential-logarithm-affine"
_INTEGER_BASE = r"(?:[2-9]|[1-9]\d+)"
_FORMULA = re.compile(
    rf"(?P<outer>{_INTEGER_BASE})\^\{{\\log_(?P<log_base>\{{?\(?{_INTEGER_BASE}\)?\}}?)\s*(?:\((?P<parenthesized_inner>[^{{}}]+)\)|(?P<bare_inner>[^{{}}]+))\}}=(?P<right>[1-9]\d*)"
)
_PARENTHESIZED_BASE = re.compile(rf"\\log_\{{\((?P<base>{_INTEGER_BASE})\)\}}")


class UnsupportedCondition(ValueError):
    pass


def _power_degree(value: int, primitive: int) -> int:
    current, degree = primitive, 1
    while current < value:
        current *= primitive
        degree += 1
    if current != value:
        raise UnsupportedCondition("logarithm base is not a power of the outer base")
    return degree


def _base_latex(value: int) -> str:
    return str(value) if value < 10 else f"{{{value}}}"


def _exact_power(value: int, base: int) -> int | None:
    exponent = 0
    current = 1
    while current < value:
        current *= base
        exponent += 1
    return exponent if current == value else None


def _build_plan(formula: str) -> RepairPlan:
    match = _FORMULA.fullmatch(formula)
    if not match:
        raise UnsupportedCondition("unsupported exponential logarithm equation")
    outer = int(match.group("outer"))
    log_base = int(match.group("log_base").strip("{}()"))
    degree = _power_degree(log_base, outer)
    inner = match.group("parenthesized_inner") or match.group("bare_inner")
    try:
        constant, coefficient = _parse_linear(inner)
    except ValueError as error:
        raise UnsupportedCondition("logarithm argument must be affine") from error
    if coefficient == 0:
        raise UnsupportedCondition("logarithm argument must contain x")
    right = int(match.group("right"))
    value = right**degree
    result = Fraction(value - constant, coefficient)
    if constant + coefficient * result <= 0:
        raise UnsupportedCondition("logarithm argument must be positive")
    try:
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("answer does not terminate") from error
    log_base_latex = _base_latex(log_base)
    exponent = format_latex_fraction(Fraction(1, degree))
    answer_latex = answer.replace(",", "{,}")
    main_content = (
        '<p>Используя формулу <span data-inline-latex="a^{\\log_b c}=c^{\\log_b a}"></span>, получаем:</p>'
        f'<center><p><span data-inline-latex="{outer}^{{\\log_{log_base_latex} ({inner})}}={right}'
        f'\\iff \\begin{{cases}}({inner})^{{\\log_{log_base_latex} {outer}}}={right}\\\\{inner}\\gt 0\\end{{cases}}'
        f'\\quad \\iff ({inner})^{{{exponent}}}={right}'
        f'\\iff {inner}={value}\\iff x={answer_latex}"></span>.</p></center>'
    )
    right_as_outer_power = _exact_power(right, outer)
    if right_as_outer_power is not None:
        alternative = (
            f'<center><p><span data-inline-latex="{outer}^{{\\log_{log_base_latex} ({inner})}}={right}'
            f'\\iff {outer}^{{\\log_{log_base_latex} ({inner})}}={outer}^{{{right_as_outer_power}}}'
            f'\\iff \\log_{log_base_latex} ({inner})={right_as_outer_power}'
            f'\\iff {inner}={log_base_latex}^{{{right_as_outer_power}}}'
            f'\\iff {inner}={value}\\iff x={answer_latex}"></span></p></center>'
        )
    else:
        alternative = (
            f'<center><p><span data-inline-latex="{outer}^{{\\log_{log_base_latex} ({inner})}}={right}'
            f'\\iff {log_base_latex}^{{\\log_{log_base_latex} ({inner})}}={right}^{{{degree}}}'
            f'\\iff {inner}={value}\\iff x={answer_latex}"></span></p></center>'
        )
    solution = (
        '<section data-content-kind="solution" data-solution-title="Решение">'
        f"{main_content}</section>"
        '<section data-content-kind="solution" data-solution-title="Приведём другое решение.">'
        f"{alternative}</section>"
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def _normalize_formula(formula: str) -> str:
    normalized = _PARENTHESIZED_BASE.sub(lambda m: f"\\log_{_base_latex(int(m.group('base')))}", formula)
    match = _FORMULA.fullmatch(re.sub(r"\s+", "", normalized))
    if match and match.group("bare_inner"):
        base = int(match.group("log_base").strip("{}()"))
        return (
            f"{match.group('outer')}^{{\\log_{_base_latex(base)} "
            f"({match.group('bare_inner')})}}={match.group('right')}"
        )
    return normalized


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = context.get("normalized_content") or {}
    condition = _section(content, "condition")
    if not condition:
        raise UnsupportedCondition("missing condition")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(spans) != 1:
        raise UnsupportedCondition("condition must have one formula")
    original = str(spans[0].get("data-inline-latex") or "")
    normalized = _normalize_formula(original)
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
