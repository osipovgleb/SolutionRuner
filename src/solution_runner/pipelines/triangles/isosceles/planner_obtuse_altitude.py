"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27345_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side altitude-to-vertex-sine repair for 27345."""

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
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    if side_match is None or altitude_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and altitude AH")
    request = _request_text(condition_html)
    if not re.search(
        r"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?ACB\b",
        request,
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request sin ACB")
    side = _parse_positive_value(side_match.group(1))
    altitude = _parse_positive_value(altitude_match.group(1))
    if sp.simplify(side - altitude).is_positive is not True:
        raise IsoscelesTrianglePlanError("AH must be less than AC")
    answer = _answer_text(sp.simplify(altitude / side))
    solution_html = (
        "<p>Синусы смежных углов равны, поэтому</p>"
        '<center><p><span data-inline-latex="'
        r"\sin \angle ACB=\sin \angle ACH=\frac{AH}{AC}="
        + rf"\frac{{{_latex_number(altitude)}}}{{{_latex_number(side)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27346_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side altitude-to-vertex-cosine repair for 27346."""

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
    first_side = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    second_equal = re.search(r"\bAB\s*=\s*BC\b", formula)
    second_side = re.search(rf"\bAB\s*=\s*{number}", formula)
    first_orientation = first_side is not None and second_equal is None
    second_orientation = (
        first_side is None and second_equal is not None and second_side is not None
    )
    if first_orientation == second_orientation:
        raise IsoscelesTrianglePlanError(
            "condition has an unsupported equal-side orientation"
        )
    altitude_name = "AH" if first_orientation else "CH"
    requested_angle = "ACB" if first_orientation else "ABC"
    altitude_match = re.search(
        rf"\b{altitude_name}\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    if altitude_match is None:
        raise IsoscelesTrianglePlanError(
            f"condition must give altitude {altitude_name}"
        )
    if not re.search(
        rf"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?{requested_angle}\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError(
            f"condition must request cos {requested_angle}"
        )
    side = _parse_positive_value(
        first_side.group(1) if first_orientation else second_side.group(1)
    )
    altitude = _parse_positive_value(altitude_match.group(1))
    projection_squared = sp.simplify(side**2 - altitude**2)
    if projection_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("altitude must be less than the equal side")
    projection = sp.sqrt(projection_squared)
    answer = _answer_text(-sp.simplify(projection / side))
    relation = (
        r"\cos \angle ACB=-\cos \angle ACH=-\frac{HC}{AC}="
        r"-\frac{\sqrt{AC^{2}-AH^{2}}}{AC}="
        if first_orientation
        else r"\cos \angle ABC=-\cos \angle CBH=-\frac{BH}{BC}="
        r"-\frac{\sqrt{BC^{2}-CH^{2}}}{BC}="
    )
    side_latex = _latex_number(side)
    altitude_latex = _latex_number(altitude)
    solution_html = (
        "<p>Косинусы смежных углов противоположны, поэтому</p>"
        '<center><p><span data-inline-latex="'
        + relation
        + rf"-\frac{{\sqrt{{({side_latex})^{{2}}-({altitude_latex})^{{2}}}}}}{{{side_latex}}}="
        + rf"-\frac{{{_latex_number(projection)}}}{{{side_latex}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27347_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse equal-side altitude-to-vertex-tangent repair for 27347."""

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
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    if side_match is None or altitude_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and altitude AH")
    if not re.search(
        r"(?:тангенс(?:\s+угла)?|\\tg)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request tg ACB")
    side = _parse_positive_value(side_match.group(1))
    altitude = _parse_positive_value(altitude_match.group(1))
    projection_squared = sp.simplify(side**2 - altitude**2)
    if projection_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("AH must be less than AC")
    projection = sp.sqrt(projection_squared)
    answer = _answer_text(-sp.simplify(altitude / projection))
    side_latex = _latex_number(side)
    altitude_latex = _latex_number(altitude)
    solution_html = (
        "<p>Используем свойство смежных углов, формулу приведения, "
        "определение тангенса и теорему Пифагора:</p>"
        '<center><p><span data-inline-latex="'
        r"\tg \angle ACB=\tg (\pi-\angle ACH)=-\tg \angle ACH="
        r"-\frac{AH}{HC}=-\frac{AH}{\sqrt{AC^{2}-AH^{2}}}="
        + rf"-\frac{{{altitude_latex}}}{{\sqrt{{({side_latex})^{{2}}-({altitude_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
