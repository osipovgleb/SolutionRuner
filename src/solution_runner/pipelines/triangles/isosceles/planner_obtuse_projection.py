"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27349_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side projection-to-vertex-cosine repair for 27349."""

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
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if side_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and CH")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request cos ACB")
    side = _parse_positive_value(side_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    if sp.simplify(side - projection).is_positive is not True:
        raise IsoscelesTrianglePlanError("CH must be less than AC")
    answer = _answer_text(-sp.simplify(projection / side))
    solution_html = (
        "<p>Косинусы смежных углов противоположны, поэтому</p>"
        '<center><p><span data-inline-latex="'
        r"\cos \angle ACB=\cos (\pi-\angle ACH)=-\cos \angle ACH="
        r"-\frac{HC}{AC}="
        + rf"-\frac{{{_latex_number(projection)}}}{{{_latex_number(side)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27350_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side projection-to-vertex-tangent repair for 27350."""

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
    if not re.search(r"тупо.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an obtuse triangle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if side_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and CH")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:тангенс(?:\s+угла)?|\\tg)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request tg ACB")
    side = _parse_positive_value(side_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    altitude_squared = sp.simplify(side**2 - projection**2)
    if altitude_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("CH must be less than AC")
    altitude = sp.sqrt(altitude_squared)
    answer = _answer_text(-sp.simplify(altitude / projection))
    solution_html = (
        "<p>Используем свойство смежных углов, формулу приведения, "
        "определение тангенса и теорему Пифагора:</p>"
        '<center><p><span data-inline-latex="'
        r"\tg \angle ACB=\tg (180^{\circ}-\angle ACH)=-\tg \angle ACH="
        r"-\frac{AH}{CH}=-\frac{\sqrt{AC^{2}-CH^{2}}}{CH}="
        + rf"-\frac{{\sqrt{{({_latex_number(side)})^{{2}}-({_latex_number(projection)})^{{2}}}}}}{{{_latex_number(projection)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
