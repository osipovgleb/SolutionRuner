"""Fail-closed selector for equations reducible to ``x² = n``."""

from __future__ import annotations

from math import isqrt
import re
from typing import Any

from bs4 import BeautifulSoup

from solution_runner.pipelines.equations.group_26656 import RepairPlan


RULE = "elementary-equations-square-root-selector"

_FORMULA = re.compile(
    r"x\^\{2\}(?:-(?P<shift>[1-9]\d*))?=(?P<right>0|[1-9]\d*)"
)
_CONDITION = re.compile(
    r"Решите уравнение (?P<formula>.+)\. "
    r"Если уравнение имеет более одного корня, в ответе укажите "
    r"(?P<choice>меньший|больший) из них\."
)
_SOLUTION_INTRO = "По\u00adсле\u00adдо\u00adва\u00adтельно по\u00adлу\u00adча\u00adем:"


class UnsupportedCondition(ValueError):
    """Raised before any transformation for a condition outside this grammar."""


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
        return str(section.get("transformation_target_id") or section.get("section_id") or f"section:{key}")
    return f"section:{key}"


def _rewrite(section: dict[str, Any] | None, key: str, title: str, html: str) -> dict[str, Any]:
    return {
        "transformation_target_id": _target(section, key),
        "operation": "rewrite" if section is not None else "add",
        "value": {"title": title, "html": html, "asset_keys": []},
    }


def _condition_formula(condition: dict[str, Any]) -> tuple[str, str]:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    spans = soup.find_all("span", attrs={"data-inline-latex": True})
    if len(spans) != 1 or spans[0].get_text("", strip=True):
        raise UnsupportedCondition("condition equation markup is ambiguous")
    formula = re.sub(r"\s+", "", str(spans[0].get("data-inline-latex") or ""))
    spans[0].replace_with(formula)
    text = re.sub(r"\s+([.])", r"\1", " ".join(soup.get_text(" ", strip=True).replace("\u00ad", "").split()))
    match = _CONDITION.fullmatch(text)
    if match is None or match.group("formula") != formula:
        raise UnsupportedCondition("condition wording does not match square-root selector")
    return formula, match.group("choice")


def _build_plan(formula: str, choice: str) -> RepairPlan:
    match = _FORMULA.fullmatch(formula)
    if match is None:
        raise UnsupportedCondition("equation does not match x-squared grammar")

    shift = match.group("shift")
    right = int(match.group("right"))
    if shift is None:
        if right == 0:
            raise UnsupportedCondition("equation must have two distinct roots")
        squared_value = right
        standard_formula = formula
    else:
        if right != 0:
            raise UnsupportedCondition("shifted equation must equal zero")
        squared_value = int(shift)
        standard_formula = f"x^{{2}}={squared_value}"

    root = isqrt(squared_value)
    if root * root != squared_value:
        raise UnsupportedCondition("right side is not a positive perfect square")
    answer = str(-root if choice == "меньший" else root)
    equation_steps = formula if standard_formula == formula else f"{formula}\\iff {standard_formula}"
    solution = (
        f"<p>{_SOLUTION_INTRO}</p>"
        f'<center><p><span data-inline-latex="{equation_steps}\\iff '
        f'\\left[\\begin{{aligned}}x=-{root}\\\\x={root}\\end{{aligned}}\\right."></span> .</p></center>'
        f'<p>Таким об­ра­зом, {"мень­ший" if choice == "меньший" else "наи­боль­ший"} ко­рень '
        f'<span data-inline-latex="x={answer}"></span>.</p>'
    )
    return RepairPlan(answer=answer, condition_html="", solution_html=solution)


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    if section is None:
        return False
    return BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text("", strip=True) == expected


def build_context_repair_plan(context: dict[str, Any]) -> RepairPlan:
    """Build transformations from one assetless schema-v3 normalized context."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
        or content.get("assets") not in (None, [])
    ):
        raise UnsupportedCondition("assetless schema-v3 normalized content is required")
    condition = _section(content, "condition")
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if condition is None or tuple(condition.get("asset_keys") or ()):
        raise UnsupportedCondition("canonical assetless condition is required")

    formula, choice = _condition_formula(condition)
    planned = _build_plan(formula, choice)
    transformations: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != planned.solution_html:
        transformations.append(_rewrite(solution, "solution", "Решение", planned.solution_html))
    if not _answer_matches(answer, planned.answer):
        transformations.append(
            _rewrite(answer, "answer", "Ответ", f'<p><span data-effect="spaced">{planned.answer}</span></p>')
        )
    return RepairPlan(
        answer=planned.answer,
        condition_html="",
        solution_html=planned.solution_html,
        transformations=tuple(transformations),
    )
