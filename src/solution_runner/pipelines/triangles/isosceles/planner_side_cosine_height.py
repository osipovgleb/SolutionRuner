"""Build audited isosceles height and projection repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27328_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-cosine to side-altitude repair for 27328."""

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
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["AH"]:
        raise IsoscelesTrianglePlanError("condition must request AH")
    side_match = re.search(
        r"\bAC\s*=\s*BC\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly cos BAC")
    side_latex = side_match.group(1)
    cosine_latex = cosine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    cosine = _parse_positive_value(cosine_latex)
    sine_squared = sp.simplify(1 - cosine**2)
    if sine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(2 * side * cosine * sp.sqrt(sine_squared))
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        "равнобедренный, поэтому углы при его основании равны, а высота из "
        '<span data-inline-latex="C"></span> делит основание пополам. Тогда</p>'
        '<center><p><span data-inline-latex="'
        r"AH=AB\sin \angle ABH=AB\sin \angle BAC="
        r"2AC\cos \angle BAC\sin \angle BAC="
        r"2AC\cos \angle BAC\sqrt{1-\cos^{2} \angle BAC}="
        + rf"2\cdot {_latex_number(side)}\cdot {cosine_latex}"
        + rf"\sqrt{{1-({cosine_latex})^{{2}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27329_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-cosine to external projection repair for 27329."""

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
    side_match = re.search(
        r"\bAC\s*=\s*BC\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["BH"]:
        raise IsoscelesTrianglePlanError("condition must request BH")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly cos BAC")
    side_latex = side_match.group(1)
    cosine_latex = cosine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    cosine = _parse_positive_value(cosine_latex)
    if sp.simplify(1 - cosine).is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(2 * side * cosine**2)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        "равнобедренный, поэтому углы при его основании равны, а высота из "
        '<span data-inline-latex="C"></span> делит основание пополам. Тогда</p>'
        '<center><p><span data-inline-latex="'
        r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
        r"2AC\cos^{2} \angle BAC="
        + rf"2\cdot {_latex_number(side)}\cdot ({cosine_latex})^{{2}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
