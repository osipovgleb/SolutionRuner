"""Fail-closed shifted odd-power solver for source group 282849."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from ..core.numbers import exact_integer_root
from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError
from .equation_conditions import read_equation_prompt

RULE = "elementary-equations-282849-shifted-cube-root"
_FORMULA = re.compile(
    r"(?:(?:\(x(?P<operator>[+-])(?P<offset>\d+)\))|x)"
    r"\^\{(?P<degree>[1-9]\d*)\}=(?P<power>-?\d+)"
)


def _exact_odd_root(value: int, degree: int) -> int:
    try:
        return exact_integer_root(value, degree)
    except ValueError as error:
        raise RightTrianglePlanError(str(error)) from error


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str | None,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    """Build the parent-faithful odd-root solution from one exact condition."""
    del parent_solution_html, current_asset_content_type
    if parent_condition_asset_id not in (None, ""):
        raise RightTrianglePlanError("group 282849 must not have assets")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer = _section(content, "answer")
    solution = _section(content, "solution")
    if (
        condition is None
        or content.get("assets")
        or tuple(condition.get("asset_keys") or ())
    ):
        raise RightTrianglePlanError("condition is incomplete")
    formula = read_equation_prompt(
        str(condition.get("html") or ""), error_type=RightTrianglePlanError
    )
    match = _FORMULA.fullmatch(formula)
    if not match:
        raise RightTrianglePlanError("condition does not match a shifted odd power")
    operator = match.group("operator")
    offset = int(match.group("offset") or 0)
    degree = int(match.group("degree"))
    power = int(match.group("power"))
    if degree < 3 or degree % 2 == 0:
        raise RightTrianglePlanError("degree must be an odd integer greater than one")
    root = _exact_odd_root(power, degree)
    result = (
        root
        if operator is None
        else (root + offset if operator == "-" else root - offset)
    )
    root_phrase = {
        3: "ку­би­че­ский ко­рень",
        5: "ко­рень пятой сте­пе­ни",
        7: "ко­рень седьмой сте­пе­ни",
        9: "ко­рень девятой сте­пе­ни",
    }.get(degree, f"ко­рень сте­пе­ни {degree}")
    left_side = "x" if operator is None else f"x{operator}{offset}"
    steps = [formula, f"{left_side}=\\sqrt[{degree}]{{{power}}}", f"{left_side}={root}"]
    if offset:
        steps.append(f"x={root}{'+' if operator == '-' else '-'}{offset}")
    steps.append(f"x={result}")
    expected_solution = (
        f"<p>Из­вле­кая {root_phrase} из обеих ча­стей урав­не­ния, получаем:</p>"
        + "".join(
            f'<center><p><span data-inline-latex="{step}"></span>.</p></center>'
            for step in steps
        )
    )
    changes: list[dict[str, Any]] = []
    if solution is None or str(solution.get("html") or "") != expected_solution:
        changes.append(
            _section_transformation(solution, "solution", "Решение", expected_solution)
        )
    current_answer = (
        BeautifulSoup(str(answer.get("html") or "") if answer else "", "html.parser")
        .get_text("", strip=True)
        .replace(" ", "")
    )
    if current_answer != str(result):
        changes.append(
            _section_transformation(
                answer,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{result}</span></p>',
            )
        )
    return RepairPlan(answer=str(result), transformations=tuple(changes))
