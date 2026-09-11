"""Fail-closed planner for group 26656: one square root of an affine term."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.core.numbers import format_answer, parse_rational


RULE = "irrational-26656-square-root-affine"

_NUMBER = r"(?:\d+|\\frac\{\d+\}\{[1-9]\d*\})"
_CONSTANT_FIRST = re.compile(
    rf"\\sqrt\{{(?P<a_sign>-?)(?P<a>{_NUMBER})(?P<operation>[+-])(?P<b>{_NUMBER})?x\}}=(?P<c>{_NUMBER})"
)
_VARIABLE_FIRST = re.compile(
    rf"\\sqrt\{{(?P<b_sign>-?)(?P<b>{_NUMBER})?x(?P<operation>[+-])(?P<a>{_NUMBER})\}}=(?P<c>{_NUMBER})"
)
_VARIABLE_ONLY = re.compile(
    rf"\\sqrt\{{(?P<b_sign>-?)(?P<b>{_NUMBER})?x\}}=(?P<c>{_NUMBER})"
)


class UnsupportedCondition(ValueError):
    """Raised before any mutation when the condition is outside frozen grammar."""


@dataclass(frozen=True)
class RepairPlan:
    answer: str
    condition_html: str
    solution_html: str
    transformations: tuple[dict[str, Any], ...] = ()


def _parse_affine(formula: str) -> tuple[Any, Any, Any]:
    """Return exact ``a, b, c`` for one accepted ``sqrt(a + bx) = c`` form."""

    match = _CONSTANT_FIRST.fullmatch(formula)
    if match is not None:
        a = parse_rational(match.group("a_sign") + match.group("a"))
        b = parse_rational(match.group("b") or "1")
        if match.group("operation") == "-":
            b = -b
        return a, b, parse_rational(match.group("c"))

    match = _VARIABLE_FIRST.fullmatch(formula)
    if match is not None:
        b = parse_rational(match.group("b_sign") + (match.group("b") or "1"))
        a = parse_rational(match.group("a"))
        if match.group("operation") == "-":
            a = -a
        return a, b, parse_rational(match.group("c"))

    match = _VARIABLE_ONLY.fullmatch(formula)
    if match is not None:
        return (
            parse_rational("0"),
            parse_rational(match.group("b_sign") + (match.group("b") or "1")),
            parse_rational(match.group("c")),
        )
    raise UnsupportedCondition("unsupported square-root affine equation")


def build_repair_plan(formula: str) -> RepairPlan:
    """Compute exactly for ``sqrt(a ± bx) = c`` with rational coefficients."""
    a, b, c = _parse_affine(formula)
    if b == 0 or c < 0:
        raise UnsupportedCondition("invalid affine coefficient or root value")
    answer = (c * c - a) / b
    squared = c * c
    rendered_answer = format_answer(answer, allow_latex_fraction=True)
    first = f"{a} + {b}x={squared}"
    solution = (
        "<p>Обе части уравнения неотрицательны, поэтому возведём их в квадрат:</p>"
        f'<center><p><span data-inline-latex="{formula}\\iff {first}\\iff x={rendered_answer}"></span>.</p></center>'
    )
    return RepairPlan(
        answer=rendered_answer,
        condition_html=f'<p>Най­ди­те ко­рень урав­не­ния <span data-inline-latex="{formula}"></span>.</p>',
        solution_html=solution,
    )


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [
        section
        for section in content.get("sections", [])
        if isinstance(section, dict) and section.get("key") == key
    ]
    if len(matches) > 1:
        raise UnsupportedCondition(f"multiple {key} sections")
    return matches[0] if matches else None


def _target(section: dict[str, Any] | None, key: str) -> str:
    if section is not None:
        exact = str(section.get("transformation_target_id") or "")
        if exact:
            return exact
        section_id = str(section.get("section_id") or "")
        if section_id:
            return f"section:{section_id}"
    return f"section:{key}"


def _rewrite(
    section: dict[str, Any] | None,
    key: str,
    title: str,
    html: str,
) -> dict[str, Any]:
    return {
        "transformation_target_id": _target(section, key),
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    if section is None:
        return False
    text = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        "", strip=True
    )
    try:
        current = parse_rational(text)
        wanted = parse_rational(expected)
    except ValueError:
        return False
    return current == wanted


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build minimal transformations from one schema-v3 problem context."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise UnsupportedCondition("schema-v3 normalized content is required")
    if content.get("assets") not in (None, []):
        raise UnsupportedCondition("group 26656 does not allow assets")
    condition = _section(content, "condition")
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical condition is required")
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    if not soup.select("span[data-inline-latex]") and soup.find("sup"):
        # A few source-group items encode an exponential equation as HTML.
        # Reuse its existing strict parser instead of treating it as ambiguous.
        from solution_runner.pipelines.equations.group_26650 import (
            build_context_repair_plan as build_exponential_context_repair_plan,
        )

        return build_exponential_context_repair_plan(context)
    spans = soup.find_all("span")
    if len(spans) != 1 or spans[0].get_text("", strip=True):
        raise UnsupportedCondition("condition equation is ambiguous")
    if set(spans[0].attrs) != {"data-inline-latex"}:
        raise UnsupportedCondition("condition equation markup is unsupported")
    formula = str(spans[0].get("data-inline-latex") or "")
    formula_is_outside_introductory_paragraph = spans[0].parent.name != "p"
    spans[0].replace_with(formula)
    visible = " ".join(
        soup.get_text(" ", strip=True).replace("\u00ad", "").split()
    )
    visible = re.sub(r"\s+([.])", r"\1", visible)
    if visible not in {
        f"{intro} {formula}{ending}"
        for intro in ("Найдите корень уравнения", "Найдите корень уравнения:", "Решите уравнение", "Решите уравнение:")
        for ending in ("", ".")
    }:
        raise UnsupportedCondition("condition does not match group 26656")
    planned = build_repair_plan(formula)
    transformations: list[dict[str, Any]] = []
    if formula_is_outside_introductory_paragraph:
        transformations.append(
            _rewrite(condition, "condition", "Условие", planned.condition_html)
        )
    if solution is None or str(solution.get("html") or "") != planned.solution_html:
        transformations.append(
            _rewrite(solution, "solution", "Решение", planned.solution_html)
        )
    if not _answer_matches(answer, planned.answer):
        transformations.append(
            _rewrite(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{planned.answer}</span></p>',
            )
        )
    return RepairPlan(
        answer=planned.answer,
        condition_html=planned.condition_html,
        solution_html=planned.solution_html,
        transformations=tuple(transformations),
    )
