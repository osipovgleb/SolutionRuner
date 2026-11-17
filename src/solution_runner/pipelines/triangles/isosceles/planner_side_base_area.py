"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27619_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the side-and-base-to-area repair for group 27619."""

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
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    side_match = re.search(
        rf"боков[^.]*сторон[^.]*равна\s*{number}",
        formula,
        re.IGNORECASE,
    )
    base_match = re.search(
        rf"основан[^.]*равно\s*{number}",
        formula,
        re.IGNORECASE,
    )
    if side_match is None or base_match is None:
        raise IsoscelesTrianglePlanError(
            "condition must give the equal side and base lengths"
        )
    side = _parse_positive_value(side_match.group(1))
    base = _parse_positive_value(base_match.group(1))
    half_base = sp.simplify(base / 2)
    radicand = sp.simplify(side**2 - half_base**2)
    if radicand <= 0:
        raise IsoscelesTrianglePlanError(
            "side and base do not form a nondegenerate triangle"
        )
    altitude = sp.sqrt(radicand)
    area = sp.simplify(base * altitude / 2)
    answer = _answer_text(area)
    solution_html = (
        "<p>Высота равнобедренного треугольника, проведённая к основанию, "
        "делит основание пополам. По теореме Пифагора найдём высоту:</p>"
        '<center><p><span data-inline-latex="'
        r"h=\sqrt{a^{2}-\left(\frac{b}{2}\right)^{2}}="
        + rf"\sqrt{{({_latex_number(side)})^{{2}}-({_latex_number(half_base)})^{{2}}}}={_latex_number(altitude)}"
        + '"></span>.</p></center>'
        "<p>Тогда площадь треугольника равна</p>"
        '<center><p><span data-inline-latex="'
        r"S=\frac{1}{2}bh="
        + rf"\frac{{1}}{{2}}\cdot {_latex_number(base)}\cdot {_latex_number(altitude)}={answer.replace(',', '{,}')}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
