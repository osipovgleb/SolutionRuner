"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27589_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 30-degree vertex-angle area repair for group 27589."""

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
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    request = _request_text(condition_html)
    if not re.search(r"площад", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the triangle area")
    if not re.search(
        r"(?:30\s*(?:\^\{?\\circ\}?|°)|угол\s+C\s+равен\s+30)", formula, re.IGNORECASE
    ):
        raise IsoscelesTrianglePlanError("condition must give a 30-degree vertex angle")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    named_side = re.search(rf"\bAC\s*=\s*BC\s*=\s*{number}", formula)
    verbal_side = re.search(
        rf"боков[^.]*сторон[^.]*равна\s*{number}",
        formula,
        re.IGNORECASE,
    )
    side_latex = (
        named_side.group(1)
        if named_side is not None
        else verbal_side.group(1)
        if verbal_side is not None
        else ""
    )
    if not side_latex:
        raise IsoscelesTrianglePlanError("condition must give the equal side length")
    side = _parse_positive_value(side_latex)
    answer = _answer_text(sp.simplify(side**2 / 4))
    solution_html = (
        "<p>Площадь треугольника равна половине произведения двух сторон "
        "на синус угла между ними. Поэтому</p>"
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 30^{\circ}="
        + rf"\frac{{1}}{{2}}\cdot ({_latex_number(side)})^{{2}}\cdot \frac{{1}}{{2}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27590_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 150-degree vertex-angle area repair for group 27590."""

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
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    if not re.search(r"площад", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the triangle area")
    if not re.search(r"150\s*(?:\^\{?\\circ\}?|°)", formula):
        raise IsoscelesTrianglePlanError(
            "condition must give a 150-degree vertex angle"
        )
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(
        rf"боков[^.]*сторон[^.]*равна\s*{number}",
        formula,
        re.IGNORECASE,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give the equal side length")
    side = _parse_positive_value(side_match.group(1))
    answer = _answer_text(sp.simplify(side**2 / 4))
    solution_html = (
        "<p>Площадь треугольника равна половине произведения двух сторон "
        "на синус угла между ними. Поэтому</p>"
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 150^{\circ}="
        r"\frac{1}{2}a^{2}\sin 30^{\circ}="
        + rf"\frac{{1}}{{2}}\cdot ({_latex_number(side)})^{{2}}\cdot \frac{{1}}{{2}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27620_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 30-degree area-to-equal-side repair for group 27620."""

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
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    if not re.search(r"30\s*(?:\^\{?\\circ\}?|°)", formula):
        raise IsoscelesTrianglePlanError("condition must give a 30-degree vertex angle")
    request = _request_text(condition_html)
    if not re.search(r"боков", request, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the equal side")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    area_match = re.search(rf"площад[^.]*равна\s*{number}", formula, re.IGNORECASE)
    if area_match is None:
        raise IsoscelesTrianglePlanError("condition must give the triangle area")
    area = _parse_positive_value(area_match.group(1))
    side = sp.simplify(2 * sp.sqrt(area))
    answer = _answer_text(side)
    solution_html = (
        "<p>Площадь треугольника равна половине произведения двух сторон "
        "на синус угла между ними:</p>"
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 30^{\circ}=\frac{a^{2}}{4}" + '"></span>.</p></center>'
        "<p>Следовательно,</p>"
        '<center><p><span data-inline-latex="'
        + rf"a=2\sqrt{{S}}=2\sqrt{{{_latex_number(area)}}}={answer.replace(',', '{,}')}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27621_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the 150-degree area-to-equal-side repair for group 27621."""

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
    formula = _formula_text(condition_html)
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    if not re.search(r"150\s*(?:\^\{?\\circ\}?|°)", formula):
        raise IsoscelesTrianglePlanError(
            "condition must give a 150-degree vertex angle"
        )
    if not re.search(r"боков", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the equal side")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    area_match = re.search(rf"площад[^.]*равна\s*{number}", formula, re.IGNORECASE)
    if area_match is None:
        raise IsoscelesTrianglePlanError("condition must give the triangle area")
    area = _parse_positive_value(area_match.group(1))
    side = sp.simplify(2 * sp.sqrt(area))
    answer = _answer_text(side)
    solution_html = (
        "<p>Площадь треугольника равна половине произведения двух сторон "
        "на синус угла между ними:</p>"
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}a^{2}\sin 150^{\circ}="
        r"\frac{1}{2}a^{2}\sin 30^{\circ}=\frac{a^{2}}{4}" + '"></span>.</p></center>'
        "<p>Следовательно,</p>"
        '<center><p><span data-inline-latex="'
        + rf"a=2\sqrt{{S}}=2\sqrt{{{_latex_number(area)}}}={answer.replace(',', '{,}')}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
