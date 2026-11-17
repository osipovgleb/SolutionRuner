"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27792_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equilateral-side-to-height repair for group 27792."""

    from .planner import (
        _answer_text,
        _build_missing_solution_plan,
        _formula_text,
        _latex_number,
        _normalized_content,
        _parse_positive_value,
        _request_text,
        _section,
    )

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    side_match = re.search(r"\bAB\s*=\s*BC\s*=\s*AC\s*=\s*([^,;.]+)", formula)
    if side_match is None:
        raise IsoscelesTrianglePlanError(
            "condition must declare AB=BC=AC and give the side"
        )
    if not re.search(
        r"(?:высот[^.]*\bCH\b|\bCH\b[^.]*высот)",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request height CH")
    side_latex = side_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    height = sp.simplify(side * sp.sqrt(3) / 2)
    answer = _answer_text(height)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равносторонний, '
        'значит, все его углы равны <span data-inline-latex="60^{\\circ}"></span>. Получаем:</p>'
        '<center><p><span data-inline-latex="'
        + rf"CH=AC\sin \angle A={side_latex}\sin 60^{{\circ}}={side_latex}\cdot \frac{{\sqrt{{3}}}}{{2}}={_latex_number(height)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27793_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equilateral-height-to-side repair for group 27793."""

    from .planner import (
        _answer_text,
        _build_missing_solution_plan,
        _formula_text,
        _inline_formulas,
        _latex_number,
        _normalized_content,
        _parse_positive_value,
        _request_text,
        _section,
    )

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"равно.*сторон", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError(
            "condition must declare an equilateral triangle"
        )
    if not re.search(r"высот[^.]*\bCH\b|\bCH\b[^.]*высот", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must give height CH")
    request = _request_text(condition_html)
    if not re.search(r"сторон", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the triangle sides")
    values = _inline_formulas(condition_html)
    if len(values) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly one height value")
    height_latex = values[0].strip()
    height = _parse_positive_value(height_latex)
    side = sp.simplify(2 * height / sp.sqrt(3))
    answer = _answer_text(side)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равносторонний, '
        'значит, все его углы равны <span data-inline-latex="60^{\\circ}"></span>. Получаем:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AC=\frac{{CH}}{{\sin \angle A}}=\frac{{{height_latex}}}{{\sin 60^{{\circ}}}}={height_latex}\cdot \frac{{2}}{{\sqrt{{3}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )
