"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27744_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side base-angle-to-vertex-angle repair for 27744."""

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
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not (
        re.search(r"\bAC\s*=\s*BC\b", formula)
        or re.search(r"сторон[^.]*\bAC\b[^.]*\bBC\b[^.]*равны", formula, re.IGNORECASE)
    ):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(
        r"угол\s+A\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)", formula, re.IGNORECASE
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle A in degrees")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    angle_a = int(angle_match.group(1))
    angle_c = 180 - 2 * angle_a
    if angle_c <= 0:
        raise IsoscelesTrianglePlanError("given angle does not form a triangle")
    answer = str(angle_c)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        "поэтому углы при основании равны:</p>"
        '<center><p><span data-inline-latex="'
        + rf"\angle A=\angle B={angle_a}^{{\circ}}"
        + '"></span>.</p></center>'
        "<p>По сумме углов треугольника</p>"
        '<center><p><span data-inline-latex="'
        + rf"\angle C=180^{{\circ}}-\angle A-\angle B=180^{{\circ}}-2\cdot {angle_a}^{{\circ}}={angle_c}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27745_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side vertex-angle-to-base-angle repair for 27745."""

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
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not (
        re.search(r"\bAC\s*=\s*BC\b", formula)
        or re.search(r"сторон[^.]*\bAC\b[^.]*\bBC\b[^.]*равны", formula, re.IGNORECASE)
    ):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)", formula, re.IGNORECASE
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C in degrees")
    if not re.search(r"угол\s+A\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle A")
    angle_c = int(angle_match.group(1))
    angle_a = sp.Rational(180 - angle_c, 2)
    if angle_a <= 0:
        raise IsoscelesTrianglePlanError("given angle does not form a triangle")
    answer = _answer_text(angle_a)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        "поэтому углы при основании равны. По сумме углов треугольника</p>"
        '<center><p><span data-inline-latex="'
        + r"\angle A=\angle B=\frac{180^{\circ}-\angle C}{2}="
        + rf"\frac{{180^{{\circ}}-{angle_c}^{{\circ}}}}{{2}}={_latex_number(angle_a)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27746_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the vertex-angle-to-exterior-base-angle repair for 27746."""

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
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not (
        re.search(r"\bAC\s*=\s*BC\b", formula)
        or re.search(r"сторон[^.]*\bAC\b[^.]*\bBC\b[^.]*равны", formula, re.IGNORECASE)
    ):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)", formula, re.IGNORECASE
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C in degrees")
    request = _request_text(condition_html)
    if not re.search(r"внешн[^.]*угол\s+CBD\b", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request exterior angle CBD")
    angle_c = int(angle_match.group(1))
    angle_b = sp.Rational(180 - angle_c, 2)
    exterior = 180 - angle_b
    if angle_b <= 0:
        raise IsoscelesTrianglePlanError("given angle does not form a triangle")
    answer = _answer_text(exterior)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        "поэтому углы при основании равны:</p>"
        '<center><p><span data-inline-latex="'
        + r"\angle B=\frac{180^{\circ}-\angle C}{2}="
        + rf"\frac{{180^{{\circ}}-{angle_c}^{{\circ}}}}{{2}}={_latex_number(angle_b)}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Внешний угол <span data-inline-latex="CBD"></span> смежный с углом '
        '<span data-inline-latex="B"></span>, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle CBD=180^{{\circ}}-\angle B=180^{{\circ}}-{_latex_number(angle_b)}^{{\circ}}={_latex_number(exterior)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27747_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the exterior-base-angle-to-vertex-angle repair for 27747."""

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
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    exterior_match = re.search(
        r"(?:в|B)нешн[^.]*угол\s+при\s+вершин[^.]*B[^.]*равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if exterior_match is None:
        raise IsoscelesTrianglePlanError("condition must give the exterior angle at B")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    exterior = int(exterior_match.group(1))
    angle_b = 180 - exterior
    angle_c = 180 - 2 * angle_b
    if angle_b <= 0 or angle_c <= 0:
        raise IsoscelesTrianglePlanError(
            "given exterior angle does not form a triangle"
        )
    answer = str(angle_c)
    solution_html = (
        '<p>Внутренний угол <span data-inline-latex="B"></span> смежный с данным внешним углом, поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle B=180^{{\circ}}-{exterior}^{{\circ}}={angle_b}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        'поэтому <span data-inline-latex="\angle A=\angle B"></span>. Тогда</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle C=180^{{\circ}}-2\angle B=180^{{\circ}}-2\cdot {angle_b}^{{\circ}}={angle_c}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27748_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the exterior-vertex-angle-to-base-angle repair for 27748."""

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
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if not re.search(r"\bAB\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AB=BC")
    exterior_match = re.search(
        r"(?:в|B)нешн[^.]*угол\s+при\s+вершин[^.]*B[^.]*равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if exterior_match is None:
        raise IsoscelesTrianglePlanError("condition must give the exterior angle at B")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    exterior = int(exterior_match.group(1))
    angle_b = 180 - exterior
    angle_c = sp.Rational(exterior, 2)
    if angle_b <= 0:
        raise IsoscelesTrianglePlanError(
            "given exterior angle does not form a triangle"
        )
    answer = _answer_text(angle_c)
    solution_html = (
        '<p>Внутренний угол <span data-inline-latex="B"></span> смежный с данным внешним углом:</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle B=180^{{\circ}}-{exterior}^{{\circ}}={angle_b}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>Треугольник <span data-inline-latex="ABC"></span> равнобедренный, '
        "поэтому углы при основании равны:</p>"
        '<center><p><span data-inline-latex="'
        + r"\angle C=\frac{180^{\circ}-\angle B}{2}="
        + rf"\frac{{180^{{\circ}}-{angle_b}^{{\circ}}}}{{2}}={_latex_number(angle_c)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )
