"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27750_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the larger-to-smaller-angle repair for group 27750."""

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
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    larger_match = re.search(
        r"больш[^.]*угол[^.]*равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if larger_match is None:
        raise IsoscelesTrianglePlanError("condition must give the larger angle")
    if not re.search(r"меньш[^.]*угол", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the smaller angle")
    larger = int(larger_match.group(1))
    smaller = sp.Rational(180 - larger, 2)
    if larger <= 60 or smaller <= 0:
        raise IsoscelesTrianglePlanError("given angle is not the unique larger angle")
    answer = _answer_text(smaller)
    solution_html = (
        "<p>Данный больший угол является углом при вершине. Два угла при основании "
        "равнобедренного треугольника равны, поэтому меньший угол равен</p>"
        '<center><p><span data-inline-latex="'
        + rf"\frac{{180^{{\circ}}-{larger}^{{\circ}}}}{{2}}={_latex_number(smaller)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27754_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the angle-difference-to-smaller-angle repair for 27754."""

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
    if not re.search(r"равно.*бедрен", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an isosceles triangle")
    difference_match = re.search(
        r"один\s+угол[^.]*на\s*(\d+)\s*(?:\^\{?\\circ\}?|°)[^.]*больше\s+друг",
        formula,
        re.IGNORECASE,
    )
    if difference_match is None:
        raise IsoscelesTrianglePlanError("condition must give the angle difference")
    if not re.search(r"меньш[^.]*угол", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request the smaller angle")
    difference = int(difference_match.group(1))
    smaller = sp.Rational(180 - difference, 3)
    if smaller <= 0:
        raise IsoscelesTrianglePlanError("given difference does not form a triangle")
    answer = _answer_text(smaller)
    solution_html = (
        '<p>Пусть меньший угол равен <span data-inline-latex="x^{\\circ}"></span>. '
        "Два меньших угла при основании равны, а больший угол равен "
        f'<span data-inline-latex="(x+{difference})^{{\\circ}}"></span>. По сумме углов треугольника</p>'
        '<center><p><span data-inline-latex="'
        + rf"2x+(x+{difference})=180\iff 3x={180 - difference}\iff x={_latex_number(smaller)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27760_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the altitude-angle-to-vertex-angle repair for group 27760."""

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
    if not re.search(r"\bAD\b[^.]*высот|высот[^.]*\bAD\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AD as an altitude")
    angle_match = re.search(
        r"угол\s+BAD\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|°)",
        formula,
        re.IGNORECASE,
    )
    if angle_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle BAD")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    angle_bad = int(angle_match.group(1))
    angle_b = 90 - angle_bad
    angle_c = 2 * angle_bad
    if angle_bad <= 0 or angle_b <= 0:
        raise IsoscelesTrianglePlanError(
            "given altitude angle does not form a triangle"
        )
    answer = str(angle_c)
    solution_html = (
        '<p>Так как <span data-inline-latex="AD"></span> — высота, '
        '<span data-inline-latex="\\triangle ABD"></span> прямоугольный. Поэтому</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle B=90^{{\circ}}-\angle BAD=90^{{\circ}}-{angle_bad}^{{\circ}}={angle_b}^{{\circ}}"
        + '"></span>.</p></center>'
        '<p>В равнобедренном <span data-inline-latex="\\triangle ABC"></span> '
        '<span data-inline-latex="\\angle A=\\angle B"></span>, следовательно,</p>'
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
