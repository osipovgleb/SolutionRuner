"""Fail-closed planner for odd-degree roots of affine expressions."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import (
    NumberFormatError,
    exact_integer_root,
    format_answer,
    format_latex_fraction,
)
from solution_runner.pipelines.equations.group_26656 import RepairPlan


RULE = "irrational-27466-odd-root-affine"

_CONSTANT_FIRST = re.compile(
    r"(?P<constant>-?\d+)(?P<operation>[+-])(?P<coefficient>-?\d*)x"
)
_VARIABLE_FIRST = re.compile(
    r"(?P<coefficient>-?\d*)x(?P<operation>[+-])(?P<constant>\d+)"
)
_VARIABLE_ONLY = re.compile(r"(?P<coefficient>-?\d*)x")
_FORMULA = re.compile(
    r"\\sqrt\[(?P<degree>[1-9]\d*)\]\{(?P<radicand>[^{}]+)\}=(?P<right>-?\d+)"
)


class UnsupportedCondition(ValueError):
    """Raised before any mutation for a condition outside the frozen grammar."""


def _coefficient(value: str) -> int:
    if value in ("", "+"):
        return 1
    if value == "-":
        return -1
    return int(value)


def _parse_affine(value: str) -> tuple[int, int]:
    """Return coefficient and constant for either canonical affine ordering."""

    match = _CONSTANT_FIRST.fullmatch(value)
    if match is not None:
        coefficient = _coefficient(match.group("coefficient"))
        if match.group("operation") == "-":
            coefficient = -coefficient
        return coefficient, int(match.group("constant"))
    match = _VARIABLE_FIRST.fullmatch(value)
    if match is not None:
        constant = int(match.group("constant"))
        if match.group("operation") == "-":
            constant = -constant
        return _coefficient(match.group("coefficient")), constant
    match = _VARIABLE_ONLY.fullmatch(value)
    if match is not None:
        return _coefficient(match.group("coefficient")), 0
    raise UnsupportedCondition("radicand is not a supported affine expression")


def _linear_latex(coefficient: int, constant: int) -> str:
    prefix = "" if coefficient == 1 else "-" if coefficient == -1 else str(coefficient)
    variable = f"{prefix}x"
    return variable if constant == 0 else f"{variable}{constant:+d}"


def build_repair_plan(formula: str) -> RepairPlan:
    """Solve ``root[n](ax+b)=c`` for every odd integer degree ``n >= 3``."""

    match = _FORMULA.fullmatch(formula)
    if match is None:
        raise UnsupportedCondition("unsupported odd-root affine equation")
    degree = int(match.group("degree"))
    if degree < 3 or degree % 2 == 0:
        raise UnsupportedCondition("root degree must be an odd integer at least three")
    coefficient, constant = _parse_affine(match.group("radicand"))
    if coefficient == 0:
        raise UnsupportedCondition("affine coefficient must be non-zero")
    right = int(match.group("right"))
    # This call is deliberately retained as a proof that an odd root is defined
    # for both signs; its result is the exact right-hand side itself.
    try:
        exact_integer_root(right**degree, degree)
    except NumberFormatError as error:  # defensive: should be unreachable
        raise UnsupportedCondition(str(error)) from error
    powered_right = right**degree
    result = Fraction(powered_right - constant, coefficient)
    try:
        answer = format_answer(result)
    except NumberFormatError as error:
        raise UnsupportedCondition("root does not have a terminating decimal form") from error
    result_latex = format_latex_fraction(result)
    linear = _linear_latex(coefficient, constant)
    solution_html = (
        f"<p>Возведём обе части уравнения в {degree}-ю степень:</p>"
        f'<center><p><span data-inline-latex="{formula}\\iff {linear}={powered_right}\\iff x={result_latex}"></span>.</p></center>'
    )
    return RepairPlan(
        answer=answer,
        condition_html="",
        solution_html=solution_html,
    )


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    found = [section for section in content.get("sections", []) if section.get("key") == key]
    if len(found) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return found[0] if found else None


def _rewrite(section: dict[str, Any] | None, key: str, title: str, html: str) -> dict[str, Any]:
    return {
        "transformation_target_id": str((section or {}).get("transformation_target_id") or f"section:{key}"),
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    if section is None:
        return False
    return BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text("", strip=True).replace(" ", "") == expected


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build safe section transformations from one normalized problem context."""

    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise UnsupportedCondition("schema-v3 normalized content is required")
    if content.get("assets") not in (None, []):
        raise UnsupportedCondition("odd-root affine tasks must not have assets")
    condition, answer_section, solution = (_section(content, key) for key in ("condition", "answer", "solution"))
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition is required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text("", strip=True) or set(spans[0].attrs) != {"data-inline-latex"}:
        raise UnsupportedCondition("condition equation is ambiguous")
    formula = str(spans[0].get("data-inline-latex") or "")
    spans[0].replace_with(formula)
    visible = re.sub(r"\s+([.])", r"\1", " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split()))
    accepted = {
        f"{intro} {formula}{ending}"
        for intro in ("Найдите корень уравнения", "Найдите корень уравнения:", "Решите уравнение", "Решите уравнение:")
        for ending in ("", ".")
    }
    if visible not in accepted:
        raise UnsupportedCondition("condition does not match the odd-root affine profile")
    planned = build_repair_plan(formula)
    transformations: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != planned.solution_html:
        transformations.append(_rewrite(solution, "solution", "Решение", planned.solution_html))
    if not _answer_matches(answer_section, planned.answer):
        transformations.append(_rewrite(answer_section, "answer", "Ответ", f'<p><span data-effect="spaced">{planned.answer}</span></p>'))
    return RepairPlan(
        answer=planned.answer,
        condition_html=str(condition.get("html") or ""),
        solution_html=planned.solution_html,
        transformations=tuple(transformations),
    )
