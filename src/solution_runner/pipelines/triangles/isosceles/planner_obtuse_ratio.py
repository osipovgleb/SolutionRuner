"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27351_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse altitude/projection-to-vertex-sine repair for 27351."""

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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if altitude_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError(
            "condition must give altitude AH and projection CH"
        )
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request sin ACB")
    altitude = _parse_positive_value(altitude_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    side = sp.sqrt(sp.simplify(altitude**2 + projection**2))
    answer = _answer_text(sp.simplify(altitude / side))
    solution_html = (
        '<p>По теореме Пифагора в <span data-inline-latex="\\triangle ACH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        r"AC=\sqrt{AH^{2}+CH^{2}}="
        + rf"\sqrt{{({_latex_number(altitude)})^{{2}}+({_latex_number(projection)})^{{2}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
        "<p>Синусы смежных углов равны, поэтому</p>"
        '<center><p><span data-inline-latex="'
        r"\sin \angle ACB=\sin (180^{\circ}-\angle ACH)=\sin \angle ACH="
        r"\frac{AH}{AC}="
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


def build_group_27352_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse altitude/projection-to-vertex-cosine repair for 27352."""

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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if altitude_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError(
            "condition must give altitude AH and projection CH"
        )
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request cos ACB")
    altitude = _parse_positive_value(altitude_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    side = sp.sqrt(sp.simplify(altitude**2 + projection**2))
    answer = _answer_text(-sp.simplify(projection / side))
    solution_html = (
        '<p>По теореме Пифагора в <span data-inline-latex="\\triangle ACH"></span>:</p>'
        '<center><p><span data-inline-latex="'
        r"AC=\sqrt{AH^{2}+CH^{2}}="
        + rf"\sqrt{{({_latex_number(altitude)})^{{2}}+({_latex_number(projection)})^{{2}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
        "<p>Косинусы смежных углов противоположны, поэтому</p>"
        '<center><p><span data-inline-latex="'
        r"\cos \angle ACB=\cos (180^{\circ}-\angle ACH)=-\cos \angle ACH="
        r"-\frac{CH}{AC}="
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


def build_group_27353_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the obtuse altitude/projection-to-vertex-tangent repair for 27353."""

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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    projection_match = re.search(rf"\bCH\s*=\s*{number}", formula)
    if altitude_match is None or projection_match is None:
        raise IsoscelesTrianglePlanError(
            "condition must give altitude AH and projection CH"
        )
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    if not re.search(
        r"(?:тангенс(?:\s+угла)?|\\tg)\s*(?:\\angle\s*)?ACB\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request tg ACB")
    altitude = _parse_positive_value(altitude_match.group(1))
    projection = _parse_positive_value(projection_match.group(1))
    answer = _answer_text(-sp.simplify(altitude / projection))
    solution_html = (
        "<p>Тангенсы смежных углов противоположны, поэтому</p>"
        '<center><p><span data-inline-latex="'
        r"\tg \angle ACB=\tg (180^{\circ}-\angle ACH)=-\tg \angle ACH="
        r"-\frac{AH}{CH}="
        + rf"-\frac{{{_latex_number(altitude)}}}{{{_latex_number(projection)}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
