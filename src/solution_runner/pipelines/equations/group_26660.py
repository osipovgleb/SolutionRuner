"""Fail-closed planner for group 26660: square root of one rational affine term."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import (
    format_answer,
    format_latex_fraction,
    parse_rational,
)
from solution_runner.pipelines.equations.group_26656 import RepairPlan
from solution_runner.pipelines.equations.linear_fraction import (
    solve_reciprocal_linear_equation,
)


RULE = "irrational-26660-square-root-rational-affine"

_RIGHT = r"(?P<right>-?(?:\d+(?:\{,\}\d+)?|\\frac\{[1-9]\d*\}\{[1-9]\d*\}))"
_VARIABLE_FIRST = re.compile(
    r"\\sqrt\{\\frac\{(?P<n>[1-9]\d*)\}\{(?P<b>[1-9]\d*)?x"
    rf"(?P<sign>[+-])(?P<d>[1-9]\d*)\}}\}}={_RIGHT}"
)
_CONSTANT_FIRST = re.compile(
    r"\\sqrt\{\\frac\{(?P<n>[1-9]\d*)\}\{(?P<a>[1-9]\d*)"
    rf"(?P<sign>[+-])(?P<b>[1-9]\d*)?x\}}\}}={_RIGHT}"
)
_LINEAR_NUMERATOR = re.compile(
    r"\\sqrt\{\\frac\{(?P<a>[1-9]\d*)?x(?P<sign>[+-])(?P<b>[1-9]\d*)\}\{(?P<c>[1-9]\d*)\}\}=(?P<d>[1-9]\d*)"
)


class UnsupportedCondition(ValueError):
    """Raised before any mutation for a condition outside the registered form."""


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [item for item in content.get("sections", []) if item.get("key") == key]
    if len(matches) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return matches[0] if matches else None


def _rewrite(section: dict[str, Any] | None, key: str, title: str, html: str) -> dict[str, Any]:
    target = str((section or {}).get("transformation_target_id") or "")
    if not target:
        target = f"section:{key}"
    return {
        "transformation_target_id": target,
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    if section is None:
        return False
    value = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text("", strip=True)
    try:
        return parse_rational(value) == parse_rational(expected)
    except ValueError:
        return False


def _parse(formula: str) -> tuple[int, int, int, Fraction]:
    match = _VARIABLE_FIRST.fullmatch(formula)
    if match is not None:
        numerator = int(match.group("n"))
        coefficient = int(match.group("b") or "1")
        constant = int(match.group("d"))
        if match.group("sign") == "-":
            constant = -constant
        return numerator, coefficient, constant, parse_rational(match.group("right"))
    match = _CONSTANT_FIRST.fullmatch(formula)
    if match is not None:
        coefficient = int(match.group("b") or "1")
        if match.group("sign") == "-":
            coefficient = -coefficient
        return int(match.group("n")), coefficient, int(match.group("a")), parse_rational(match.group("right"))
    raise UnsupportedCondition("unsupported square-root rational affine equation")


def _linear_latex(coefficient: int, constant: int) -> str:
    constant_part = f"+{constant}" if constant >= 0 else str(constant)
    prefix = "" if coefficient == 1 else "-" if coefficient == -1 else str(coefficient)
    return f"{prefix}x{constant_part}"


def _parse_linear_numerator(formula: str) -> tuple[int, int, int, int] | None:
    match = _LINEAR_NUMERATOR.fullmatch(formula)
    if match is None:
        return None
    constant = int(match.group("b"))
    if match.group("sign") == "-":
        constant = -constant
    return int(match.group("a") or "1"), constant, int(match.group("c")), int(match.group("d"))


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Plan exact repairs for ``sqrt(n / (bx+d)) = 1/q``."""

    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise UnsupportedCondition("schema-v3 normalized content is required")
    if content.get("assets") not in (None, []):
        raise UnsupportedCondition("group 26660 does not allow assets")
    condition, answer, solution = (_section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition is required")

    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text("", strip=True) or set(spans[0].attrs) != {"data-inline-latex"}:
        raise UnsupportedCondition("condition equation is ambiguous")
    formula = str(spans[0].get("data-inline-latex") or "")
    spans[0].replace_with(formula)
    visible = re.sub(r"\s+([.])", r"\1", " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split()))
    if visible not in {
        f"{intro} {formula}{ending}"
        for intro in ("Найдите корень уравнения", "Найдите корень уравнения:", "Решите уравнение", "Решите уравнение:")
        for ending in ("", ".")
    }:
        raise UnsupportedCondition("condition does not match group 26660")

    linear_numerator = _parse_linear_numerator(formula)
    if linear_numerator is None:
        numerator, coefficient, constant, right_value = _parse(formula)
        if right_value == 0:
            raise UnsupportedCondition("right side must be non-zero")
        squared_right = right_value * right_value
        denominator_value = Fraction(numerator, 1) / squared_right
        answer_value = solve_reciprocal_linear_equation(Fraction(numerator), Fraction(coefficient), Fraction(constant), squared_right)
        linear = _linear_latex(coefficient, constant)
        normalized_right = format_latex_fraction(right_value)
        normalized_square = format_latex_fraction(squared_right)
        original_right = formula.rsplit("=", 1)[1]
        normalization = (
            f"\\sqrt{{\\frac{{{numerator}}}{{{linear}}}}}={normalized_right}\\iff "
            if "{,}" in original_right or "." in original_right
            else ""
        )
        calculation = f"{formula}\\iff {normalization}\\frac{{{numerator}}}{{{linear}}}={normalized_square}\\iff {linear}={format_latex_fraction(denominator_value)}"
    else:
        coefficient, constant, denominator, right = linear_numerator
        linear = _linear_latex(coefficient, constant)
        squared_right = right * right
        answer_value = Fraction(denominator * squared_right - constant, coefficient)
        calculation = f"{formula}\\iff \\frac{{{linear}}}{{{denominator}}}={squared_right}\\iff {linear}={denominator * squared_right}"
    rendered_answer = format_answer(answer_value, allow_latex_fraction=True)
    solution_html = (
        "<p>Обе части уравнения неотрицательны, поэтому возведём их в квадрат:</p>"
        f'<center><p><span data-inline-latex="{calculation}\\iff x={rendered_answer}"></span>.</p></center>'
    )
    changes: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != solution_html:
        changes.append(_rewrite(solution, "solution", "Решение", solution_html))
    if not _answer_matches(answer, rendered_answer):
        changes.append(_rewrite(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{rendered_answer}</span></p>'))
    return RepairPlan(answer=rendered_answer, condition_html=str(condition.get("html") or ""), solution_html=solution_html, transformations=tuple(changes))
