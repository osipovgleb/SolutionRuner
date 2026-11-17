"""Build audited isosceles height and projection repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27324_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-tangent to opposite-side altitude repair for 27324."""

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
    if re.search(r"\bAC\s*=\s*BC\b", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["AH"]:
        raise IsoscelesTrianglePlanError("condition must request AH")
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    visible_base = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one AB length")
    tangent_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\tg\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(tangent_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly tg BAC")
    tangent_latex = tangent_assignments[0].split("=", 1)[1].strip()
    base = _parse_positive_value(base_latex)
    tangent = _parse_positive_value(tangent_latex)
    answer = _answer_text(base * tangent / sp.sqrt(1 + tangent**2))
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        "равнобедренный, поэтому углы при его основании равны. Последовательно получаем:</p>"
        '<center><p><span data-inline-latex="'
        r"AH=AB\sin \angle ABH=AB\sin \angle ABC="
        r"AB\sqrt{\frac{1}{1+\ctg^{2} \angle ABC}}="
        + rf"{_latex_number(base)}\sqrt{{\frac{{1}}{{1+\frac{{1}}{{({tangent_latex})^{{2}}}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27325_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-tangent to adjacent projection repair for 27325."""

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
    if re.search(r"\bAC\s*=\s*BC\b", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if re.findall(r"\b([ABC]H)\b", _request_text(condition_html)) != ["BH"]:
        raise IsoscelesTrianglePlanError("condition must request BH")
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    visible_base = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one AB length")
    tangent_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\tg\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(tangent_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly tg BAC")
    tangent_latex = tangent_assignments[0].split("=", 1)[1].strip()
    base = _parse_positive_value(base_latex)
    tangent = _parse_positive_value(tangent_latex)
    answer = _answer_text(base / sp.sqrt(1 + tangent**2))
    solution_html = (
        '<p>Найдём <span data-inline-latex="BH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
        r"AB\sqrt{\frac{1}{1+\tg^{2} \angle BAC}}="
        + rf"{_latex_number(base)}\sqrt{{\frac{{1}}{{1+({tangent_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
