"""Strict repair planner for elementary-equation group 26662."""

from __future__ import annotations

from fractions import Fraction
import math
import re
from typing import Any

from bs4 import BeautifulSoup

from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError


RULE = "elementary-equations-26662-fractional-linear-equation"
PARENT_PROBLEM_ID = "20bfb2f5-1f08-40f0-b0e5-e678c7fbea3e"

_CONDITION = re.compile(
    r"Найдите корень уравнения: "
    r"(?P<coefficient_sign>-?)\\frac\{(?P<numerator>[1-9]\d{0,5})\}\{(?P<denominator>[1-9]\d{0,5})\}x="
    r"(?P<right_sign>-?)"
    r"(?P<whole>[1-9]\d{0,5})"
    r"\\frac\{(?P<part_numerator>[1-9]\d{0,5})\}\{(?P<part_denominator>[1-9]\d{0,5})\}\."
)


def _canonical_section(section: dict[str, Any] | None, key: str) -> None:
    if section is None:
        return
    if (
        section.get("section_id") != f"{key}:1"
        or section.get("transformation_target_id", f"section:{key}:1")
        != f"section:{key}:1"
    ):
        raise RightTrianglePlanError("noncanonical section identity")


def _equation(
    content: dict[str, Any], condition: dict[str, Any], *, allow_negative_answer: bool
) -> tuple[str, Fraction]:
    assets = content.get("assets")
    if not isinstance(assets, list) or assets:
        raise RightTrianglePlanError("group 26662 does not allow condition assets")
    if tuple(condition.get("asset_keys") or ()):
        raise RightTrianglePlanError("condition has an unexpected asset reference")

    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    for tag in soup.find_all(True):
        allowed = {"p": set(), "span": {"data-inline-latex"}}.get(tag.name)
        if allowed is None or set(tag.attrs) != allowed:
            raise RightTrianglePlanError("condition contains unsupported markup")
    if soup.find("img") is not None:
        raise RightTrianglePlanError("condition contains an unexpected image")
    formulas = soup.find_all("span")
    if len(formulas) != 1 or formulas[0].get_text("", strip=True):
        raise RightTrianglePlanError("condition equation is ambiguous")
    formula = str(formulas[0].get("data-inline-latex") or "")
    formulas[0].replace_with(formula)
    text = soup.get_text(" ", strip=True).replace("\u00ad", "").replace("\u202f", " ")
    text = re.sub(r"\s+([.])", r"\1", " ".join(text.split()))
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise RightTrianglePlanError("condition does not match group 26662")

    values = {
        name: int(match.group(name))
        for name in ("numerator", "denominator", "whole", "part_numerator", "part_denominator")
    }
    coefficient = Fraction(values["numerator"], values["denominator"])
    right_side = Fraction(values["whole"], 1) + Fraction(
        values["part_numerator"], values["part_denominator"]
    )
    if match.group("coefficient_sign") == "-":
        coefficient = -coefficient
    if match.group("right_sign") == "-":
        right_side = -right_side
    answer = right_side / coefficient
    if answer.denominator != 1 or answer.numerator == 0 or (
        not allow_negative_answer and answer.numerator < 0
    ):
        raise RightTrianglePlanError("equation does not have a supported integral root")
    return formula, answer


def _condition_html(formula: str) -> str:
    return (
        '<p>Най­ди­те ко­рень урав­не­ния: '
        f'<span data-inline-latex="{formula}"></span>.</p>'
    )


def _answer_matches(section: dict[str, Any] | None, answer: int) -> bool:
    if section is None:
        return False
    text = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        " ", strip=True
    )
    return bool(re.fullmatch(r"-?\d+", text)) and int(text) == answer


def _solution_html(formula: str, answer: int) -> str:
    match = _CONDITION.search(f"Найдите корень уравнения: {formula}.")
    if match is None:
        raise RightTrianglePlanError("equation formula is inconsistent")
    values = {
        name: int(match.group(name))
        for name in ("numerator", "denominator", "whole", "part_numerator", "part_denominator")
    }
    coefficient_sign = -1 if match.group("coefficient_sign") == "-" else 1
    right_sign = -1 if match.group("right_sign") == "-" else 1
    numerator = values["numerator"]
    denominator = values["denominator"]
    right_numerator = values["whole"] * values["part_denominator"] + values["part_numerator"]
    right_denominator = values["part_denominator"]
    common_denominator = math.lcm(denominator, right_denominator)
    left_integer_coefficient = (
        coefficient_sign * numerator * common_denominator // denominator
    )
    right_integer_value = (
        right_sign * right_numerator * common_denominator // right_denominator
    )
    coefficient_fraction = f"{'-' if coefficient_sign < 0 else ''}\\frac{{{numerator}}}{{{denominator}}}"
    right_fraction = f"{'-' if right_sign < 0 else ''}\\frac{{{right_numerator}}}{{{right_denominator}}}"
    calculation = (
        f"{formula}\\iff "
        f"{coefficient_fraction}x={right_fraction}"
        f"\\iff {left_integer_coefficient}x={right_integer_value}\\iff x={answer}"
    )
    return (
        '<p>По­сле­до­ва­тель­но по­лу­ча­ем:</p>'
        f'<center><p> <span data-inline-latex="{calculation}"></span>. </p></center>'
    )


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
    allow_negative_answer: bool = False,
) -> RepairPlan:
    """Compute and converge one supported fractional linear equation."""

    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id not in (None, ""):
        raise RightTrianglePlanError("group 26662 must not have a parent condition asset")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution = _section(content, "solution")
    for key, section in (("condition", condition), ("answer", answer_section), ("solution", solution)):
        _canonical_section(section, key)
    if condition is None:
        raise RightTrianglePlanError("canonical condition is required")

    formula, answer_fraction = _equation(
        content, condition, allow_negative_answer=allow_negative_answer
    )
    answer = answer_fraction.numerator
    expected_condition = _condition_html(formula)
    expected_solution = _solution_html(formula, answer)
    changes: list[dict[str, Any]] = []
    if str(condition.get("html") or "") != expected_condition:
        changes.append(_section_transformation(condition, "condition", "Условие", expected_condition))
    if solution is None or str(solution.get("html") or "") != expected_solution:
        changes.append(_section_transformation(solution, "solution", "Решение", expected_solution))
    if not _answer_matches(answer_section, answer):
        changes.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=str(answer), transformations=tuple(changes))
