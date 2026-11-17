"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27797_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the altitude-and-vertex-angle-to-equal-side repair for 27797."""

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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    height_match = re.search(
        r"высот[^.]*\bAH\b\s+равна\s*([^,;.]+)", formula, re.IGNORECASE
    )
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if height_match is None or angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give altitude AH and angle C")
    request = _request_text(condition_html)
    if not re.search(r"\bAC\b", request) or re.search(
        r"\b(?:AB|BC|AH|BH|CH)\b", request
    ):
        raise IsoscelesTrianglePlanError("condition must request AC")
    height_latex = height_match.group(1).strip()
    height = _parse_positive_value(height_latex)
    angle = int(angle_match.group(1))
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("vertex angle must form a triangle")
    sine = sp.simplify(sp.sin(sp.pi * angle / 180))
    if sine.has(sp.sin):
        raise IsoscelesTrianglePlanError("vertex angle has no supported exact sine")
    side = sp.simplify(height / sine)
    answer = _answer_text(side)
    reciprocal = sp.simplify(1 / sine)
    solution_html = (
        '<p>Найдём длину стороны <span data-inline-latex="AC"></span> из '
        'прямоугольного <span data-inline-latex="\\triangle ACH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AC=\frac{{AH}}{{\sin \angle C}}=\frac{{{height_latex}}}{{\sin {angle}^{{\circ}}}}={height_latex}\cdot {_latex_number(reciprocal)}={_latex_number(side)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27798_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side-and-vertex-angle-to-altitude repair."""

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
    side_match = re.search(r"\bAC\s*=\s*BC\s*=\s*([^,;.]+)", formula)
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if side_match is None or angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and angle C")
    if not re.search(
        r"высот[^.]*\bAH\b|\bAH\b[^.]*высот",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request altitude AH")
    side_latex = side_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    angle = int(angle_match.group(1))
    if angle <= 90 or angle >= 180:
        raise IsoscelesTrianglePlanError("group 27798 requires an obtuse angle C")
    supplement = 180 - angle
    sine = sp.simplify(sp.sin(sp.pi * supplement / 180))
    if sine.has(sp.sin):
        raise IsoscelesTrianglePlanError(
            "supplementary angle has no supported exact sine"
        )
    height = sp.simplify(side * sine)
    answer = _answer_text(height)
    solution_html = (
        "<p>Так как основание высоты лежит на продолжении стороны "
        '<span data-inline-latex="BC"></span>,</p><center><p><span data-inline-latex="'
        + rf"\angle ACH=180^{{\circ}}-\angle C={supplement}^{{\circ}}"
        + '"></span>.</p></center><p>В прямоугольном '
        '<span data-inline-latex="\\triangle ACH"></span> получаем:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AH=AC\sin \angle ACH={side_latex}\sin {supplement}^{{\circ}}={side_latex}\cdot {_latex_number(sine)}={_latex_number(height)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )
