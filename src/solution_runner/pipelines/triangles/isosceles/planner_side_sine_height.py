"""Build audited isosceles height and projection repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27326_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-sine to side-altitude repair for 27326."""

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
    side_latex = side_match.group(1) if side_match is not None else ""
    if not side_latex and re.search(
        r"равно.*бедрен.*основан.*\bAB\b.*боков.*сторон.*равна",
        formula,
        re.IGNORECASE,
    ):
        standalone_values: list[str] = []
        for item in _inline_formulas(condition_html):
            if "=" in item:
                continue
            try:
                _parse_positive_value(item.strip())
            except IsoscelesTrianglePlanError:
                continue
            standalone_values.append(item.strip())
        if len(standalone_values) == 1:
            side_latex = standalone_values[0]
    if not side_latex:
        raise IsoscelesTrianglePlanError("condition must give the equal side AC=BC")
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly sin BAC")
    sine_latex = sine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    sine = _parse_positive_value(sine_latex)
    cosine_squared = sp.simplify(1 - sine**2)
    if cosine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    cosine = sp.sqrt(cosine_squared)
    answer = _answer_text(2 * side * sine * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        "равнобедренный, поэтому углы при его основании равны, а высота из "
        '<span data-inline-latex="C"></span> делит основание пополам. Тогда</p>'
        '<center><p><span data-inline-latex="'
        r"AH=AB\sin \angle ABH=AB\sin \angle BAC="
        r"2AC\cos \angle BAC\sin \angle BAC="
        r"2AC\sin \angle BAC\sqrt{1-\sin^{2} \angle BAC}="
        + rf"2\cdot {_latex_number(side)}\cdot {sine_latex}"
        + rf"\sqrt{{1-({sine_latex})^{{2}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def _parse_27327(condition_html):
    from .planner import (
        _formula_text,
        _inline_formulas,
        _parse_positive_value,
        _request_text,
    )

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
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly sin BAC")
    side_latex = side_match.group(1)
    sine_latex = sine_assignments[0].split("=", 1)[1].strip()
    side = _parse_positive_value(side_latex)
    sine = _parse_positive_value(sine_latex)
    cosine_squared = sp.simplify(1 - sine**2)
    if cosine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    return side, cosine_squared, sine_latex


def build_group_27327_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the equal-side-and-sine to external projection repair for 27327."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _condition_image_repairs,
        _latex_number,
        _normalized_content,
        _plain_html,
        _section,
        _section_transformation,
    )

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    side, cosine_squared, sine_latex = _parse_27327(condition_html)
    answer = _answer_text(2 * side * cosine_squared)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27327")
    )
    if solution_missing:
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            "равнобедренный, поэтому углы при его основании равны, а высота из "
            '<span data-inline-latex="C"></span> делит основание пополам. Имеем:</p>'
            '<center><p><span data-inline-latex="'
            r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
            r"2AC\cos^{2} \angle BAC=2AC(1-\sin^{2} \angle BAC)="
            + rf"2\cdot {_latex_number(side)}\cdot (1-({sine_latex})^{{2}})="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))
