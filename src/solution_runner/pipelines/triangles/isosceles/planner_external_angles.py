"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_676342_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the external-base-angle repair for group 676342."""

    from .planner import (
        _build_missing_solution_plan,
        _formula_text,
        _normalized_content,
        _request_text,
        _section,
    )

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if "равно" not in formula.lower() or "бедрен" not in formula.lower():
        raise IsoscelesTrianglePlanError("condition must state an isosceles triangle")
    if re.search(r"основа\S*\s+[AА][BВ]\b", formula, re.IGNORECASE) is None:
        raise IsoscelesTrianglePlanError("condition must state base AB")
    if (
        re.search(
            r"(?:вершин\S*\s+[BВ]\b|угол\s+[CС][BВ]D\b)",
            formula,
            re.IGNORECASE,
        )
        is None
    ):
        raise IsoscelesTrianglePlanError("external angle must be at vertex B")
    angle_match = re.search(
        r"внешн\S*\s+угол.*?равен\s*([0-9]+)\s*°",
        formula,
        re.IGNORECASE,
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give one external angle")
    request = _request_text(condition_html)
    if not re.search(r"угл\S*\s+[AА]\b", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle A")
    external_angle = int(angle_match.group(1))
    if external_angle <= 90 or external_angle >= 180:
        raise IsoscelesTrianglePlanError(
            "external base angle must be between 90 and 180"
        )
    base_angle = 180 - external_angle
    answer = str(base_angle)
    solution_html = (
        '<p>По свойству смежных углов</p><center><p><span data-inline-latex="'
        + rf"\angle CBA=180^{{\circ}}-\angle CBD=180^{{\circ}}-{external_angle}^{{\circ}}={base_angle}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому углы при основании <span data-inline-latex="AB"></span> равны:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle CAB=\angle CBA={base_angle}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_701874_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the apex-exterior-angle to base-angle repair for group 701874."""

    from .planner import (
        _answer_text,
        _build_missing_solution_plan,
        _formula_text,
        _latex_number,
        _normalized_content,
        _request_text,
        _section,
    )

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    formula = _formula_text(condition_html)
    if "равно" not in formula.lower() or "бедрен" not in formula.lower():
        raise IsoscelesTrianglePlanError("condition must state an isosceles triangle")
    if re.search(r"основа\S*\s+[AА][BВ]\b", formula, re.IGNORECASE) is None:
        raise IsoscelesTrianglePlanError("condition must state base AB")
    if re.search(r"вершин\S*\s+[CС]\b", formula, re.IGNORECASE) is None:
        raise IsoscelesTrianglePlanError("external angle must be at vertex C")
    angle_match = re.search(
        r"внешн\S*\s+угол.*?равен\s*([0-9]+)\s*°",
        formula,
        re.IGNORECASE,
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give one external angle")
    request = _request_text(condition_html)
    if not re.search(r"угл\S*\s+[AА][BВ][CС]\b", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle ABC")
    external_angle = int(angle_match.group(1))
    if external_angle <= 0 or external_angle >= 180:
        raise IsoscelesTrianglePlanError(
            "external apex angle must be between 0 and 180"
        )
    base_angle = sp.Rational(external_angle, 2)
    answer = _answer_text(base_angle)
    solution_html = (
        "<p>Внешний угол равен сумме двух несмежных с ним углов:</p>"
        '<center><p><span data-inline-latex="'
        + rf"\angle ABC+\angle CAB={external_angle}^{{\circ}}"
        + '"></span>.</p></center>'
        "<p>Углы при основании равнобедренного треугольника равны, поэтому</p>"
        '<center><p><span data-inline-latex="'
        + rf"\angle ABC=\angle CAB\iff 2\angle ABC={external_angle}^{{\circ}}"
        + rf"\iff \angle ABC={_latex_number(base_angle)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
