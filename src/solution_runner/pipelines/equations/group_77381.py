r"""Fail-closed plans for ``log_a(L)=log_a(R)+c`` with affine arguments."""
from __future__ import annotations

import re
from fractions import Fraction
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import NumberFormatError, format_answer, format_latex_fraction
from solution_runner.pipelines.equations.group_26646 import _log_base_latex, _section, _solution_signature
from solution_runner.pipelines.equations.group_26650 import _linear_latex, _parse_linear, _rewrite
from solution_runner.pipelines.equations.group_26656 import RepairPlan

RULE = "logarithm-77381-shifted-equal-logs"
_BASE = r"(?:[2-9]|[1-9]\d+)"
_FORMULA = re.compile(
    rf"\\log_(?P<left_base>\{{?{_BASE}\}}?)\s*\((?P<left>[^{{}}]+)\)="
    rf"\\log_(?P<right_base>\{{?{_BASE}\}}?)\s*(?:\((?P<right_parenthesized>[^{{}}]+)\)|(?P<right_bare>x))\+(?P<shift>[1-9]\d*)"
)


class UnsupportedCondition(ValueError):
    pass


def _coefficient_latex(value: int) -> str:
    return "x" if value == 1 else "-x" if value == -1 else f"{value}x"


def _inequality_steps(constant: int, coefficient: int) -> tuple[str, str, Fraction, str]:
    """Return the moved and solved forms of ``constant + coefficient*x > 0``."""

    if coefficient == 0:
        raise UnsupportedCondition("logarithm argument does not depend on x")
    moved = f"{_coefficient_latex(coefficient)}>{-constant}"
    root = Fraction(-constant, coefficient)
    comparison = ">" if coefficient > 0 else "<"
    return moved, f"x{comparison}{format_latex_fraction(root)}", root, comparison


def _strictest_inequality(
    left: tuple[str, str, Fraction, str], right: tuple[str, str, Fraction, str],
) -> tuple[str, ...]:
    """Drop the weaker bound only when the two inequalities have one direction."""

    _, left_solved, left_bound, left_sign = left
    _, right_solved, right_bound, right_sign = right
    if left_sign != right_sign:
        return left_solved, right_solved
    if left_sign == "<":
        return (left_solved if left_bound < right_bound else right_solved,)
    return (left_solved if left_bound > right_bound else right_solved,)


def _build_plan(formula: str) -> RepairPlan:
    match = _FORMULA.fullmatch(formula)
    if not match:
        raise UnsupportedCondition("unsupported shifted logarithmic equation")
    left_base = int(match.group("left_base").strip("{}"))
    right_base = int(match.group("right_base").strip("{}"))
    if left_base != right_base:
        raise UnsupportedCondition("logarithm bases must match")
    left = match.group("left")
    right = str(match.group("right_parenthesized") or match.group("right_bare") or "")
    try:
        left_constant, left_coefficient = _parse_linear(left)
        right_constant, right_coefficient = _parse_linear(right)
    except ValueError as error:
        raise UnsupportedCondition("logarithm arguments must be affine") from error
    shift = int(match.group("shift"))
    factor = left_base**shift
    coefficient = left_coefficient - factor * right_coefficient
    if coefficient == 0:
        raise UnsupportedCondition("equation has no unique root")
    result = Fraction(factor * right_constant - left_constant, coefficient)
    if right_constant + right_coefficient * result <= 0:
        raise UnsupportedCondition("logarithm argument must be positive")
    try:
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("answer does not terminate") from error
    left_inequality = _inequality_steps(left_constant, left_coefficient)
    right_inequality = _inequality_steps(right_constant, right_coefficient)
    left_moved, left_solved, _, _ = left_inequality
    right_moved, right_solved, _, _ = right_inequality
    strictest = _strictest_inequality(left_inequality, right_inequality)
    base = _log_base_latex(left_base)
    log_left = f"\\log_{base} ({left})"
    log_right = f"\\log_{base} ({right})"
    scaled_right = _linear_latex(factor * right_constant, factor * right_coefficient)
    exact = format_latex_fraction(result)
    solution = (
        f'<p>Заметим, что свободный член равен <span data-inline-latex="{shift}=\\log_{base} {left_base}^{{{shift}}}"></span>:</p>'
        f'<center><p><span data-inline-latex="{log_left}={log_right}+{shift}'
        f'\\iff {log_left}={log_right}+\\log_{base} {left_base}^{{{shift}}}'
        f'\\iff {log_left}=\\log_{base} ({left_base}^{{{shift}}}({right}))'
        f'\\iff \\begin{{cases}}{left}\\gt 0\\\\{right}\\gt 0\\\\{left}={left_base}^{{{shift}}}({right})\\end{{cases}}\\quad '
        f'\\iff \\begin{{cases}}{left_moved}\\\\{right_moved}\\\\{left}={scaled_right}\\end{{cases}}'
        f'\\iff \\begin{{cases}}{left_solved}\\\\{right_solved}\\\\x={exact}\\end{{cases}}\\quad '
        f'\\iff \\begin{{cases}}{"\\\\".join(strictest)}\\\\x={exact}\\end{{cases}}\\quad \\iff x={exact}"></span>.</p></center>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    content = context.get("normalized_content") or {}
    condition = _section(content, "condition")
    if not condition:
        raise UnsupportedCondition("missing condition")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    formulas = [str(node.get("data-inline-latex") or "") for node in soup.find_all("span", attrs={"data-inline-latex": True})]
    if len(formulas) != 1:
        raise UnsupportedCondition("condition must have one logarithmic formula")
    plan = _build_plan(re.sub(r"\s+", "", formulas[0]))
    answer_section = _section(content, "answer")
    solution_section = _section(content, "solution")
    transformations: list[dict[str, Any]] = []
    if not solution_section or _solution_signature(str(solution_section.get("html") or "")) != _solution_signature(plan.solution_html):
        transformations.append(_rewrite(solution_section, "solution", "Решение", plan.solution_html))
    if not answer_section or BeautifulSoup(str(answer_section.get("html") or ""), "html.parser").get_text(" ", strip=True) != plan.answer:
        transformations.append(_rewrite(answer_section, "answer", "Ответ", f"<p>{plan.answer}</p>"))
    return RepairPlan(answer=plan.answer, condition_html="", solution_html=plan.solution_html, transformations=tuple(transformations))
