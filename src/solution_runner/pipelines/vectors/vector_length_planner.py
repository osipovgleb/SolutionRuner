"""Strict repair planner for vector group 27663."""

from __future__ import annotations

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


RULE = "vector-27663-coordinate-length"
PARENT_PROBLEM_ID = "55451a3e-8a4a-4c1d-bfd9-106ecf986590"

_CONDITION = re.compile(
    r"Найдите длину вектора "
    r"\\(?:vec|overrightarrow)\{a\}\s*=?\s*\("
    r"(?P<x>-?\d{1,6})\s*(?:[;,]|\{,\})\s*(?P<y>-?\d{1,6})\)\."
)
_VECTOR_FORMULA = re.compile(
    r"\\(?:vec|overrightarrow)\{a\}\s*=?\s*\("
    r"(?P<x>-?\d{1,6})\s*(?:[;,]|\{,\})\s*(?P<y>-?\d{1,6})\)"
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


def _coordinates(content: dict[str, Any], condition: dict[str, Any]) -> tuple[int, int]:
    assets = content.get("assets")
    if not isinstance(assets, list) or assets:
        raise RightTrianglePlanError("vector group 27663 does not allow assets")
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
        raise RightTrianglePlanError("condition vector formula is ambiguous")
    formula = str(formulas[0].get("data-inline-latex") or "")
    formula_match = _VECTOR_FORMULA.fullmatch(formula)
    if formula_match is None:
        raise RightTrianglePlanError("condition vector expression is unsupported")
    formulas[0].replace_with(formula)
    text = soup.get_text(" ", strip=True).replace("\u00ad", "").replace("\u202f", " ")
    text = re.sub(r"\s+([.])", r"\1", " ".join(text.split()))
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise RightTrianglePlanError("condition does not match vector group 27663")
    parsed = tuple(int(match.group(name)) for name in ("x", "y"))
    formula_values = tuple(int(formula_match.group(name)) for name in ("x", "y"))
    if parsed != formula_values:
        raise RightTrianglePlanError("condition coordinate parsing is inconsistent")
    return parsed


def _answer_matches(section: dict[str, Any] | None, answer: int) -> bool:
    if section is None:
        return False
    text = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        " ", strip=True
    )
    return bool(re.fullmatch(r"\d+", text)) and int(text) == answer


def _coordinate_square(value: int) -> str:
    return f"({value})^{{2}}" if value < 0 else f"{value}^{{2}}"


def _solution_html(x: int, y: int, answer: int) -> str:
    square_sum = x * x + y * y
    substitution = (
        rf"\left|\vec{{a}}\right|="
        rf"\sqrt{{{_coordinate_square(x)}+{_coordinate_square(y)}}}="
        rf"\sqrt{{{square_sum}}}={answer}"
    )
    return (
        '<p>Длина век­то­ра с ко­ор­ди­на­та­ми '
        '<span data-inline-latex="(x;y)"></span> вы­чис­ля­ет­ся по фор­му­ле '
        '<span data-inline-latex="\\left|\\vec{a}\\right|='
        '\\sqrt{x^{2}+y^{2}}"></span>.</p>'
        '<p>Под­ста­вим ко­ор­ди­на­ты дан­но­го век­то­ра:</p>'
        '<center><p> '
        f'<span data-inline-latex="{substitution}"></span>.</p></center>'
    )


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    """Compute the coordinate-vector length and converge solution and answer."""

    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id:
        raise RightTrianglePlanError("vector group 27663 must not have a parent asset")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution = _section(content, "solution")
    for key, section in (
        ("condition", condition),
        ("answer", answer_section),
        ("solution", solution),
    ):
        _canonical_section(section, key)
    if condition is None:
        raise RightTrianglePlanError("canonical condition is required")

    x, y = _coordinates(content, condition)
    square_sum = x * x + y * y
    answer = math.isqrt(square_sum)
    if answer * answer != square_sum:
        raise RightTrianglePlanError("coordinates do not produce a supported exact answer")
    expected_solution = _solution_html(x, y, answer)

    changes: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != expected_solution:
        changes.append(
            _section_transformation(solution, "solution", "Решение", expected_solution)
        )
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
