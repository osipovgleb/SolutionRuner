"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27794_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-altitude-to-vertex-angle repair for 27794."""

    from .planner import (
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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    base_match = re.search(r"\bAB\s*=\s*(.+?)(?=\s+Найд|[,;.]|$)", formula)
    if base_match is None:
        raise IsoscelesTrianglePlanError("condition must give base AB")
    if not re.search(r"высот[^.]*\bCH\b|\bCH\b[^.]*высот", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must give altitude CH")
    if not re.search(r"угол\s+C\b", _request_text(condition_html), re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    height_values = tuple(
        value.strip() for value in _inline_formulas(condition_html) if "=" not in value
    )
    if len(height_values) != 1:
        raise IsoscelesTrianglePlanError(
            "condition must give exactly one altitude value"
        )
    base_latex = base_match.group(1).strip()
    height_latex = height_values[0]
    base = _parse_positive_value(base_latex)
    height = _parse_positive_value(height_latex)
    half_base = sp.simplify(base / 2)
    side = sp.simplify(sp.sqrt(half_base**2 + height**2))
    if sp.simplify(side - base) != 0:
        raise IsoscelesTrianglePlanError(
            "base and altitude do not produce an equilateral triangle"
        )
    answer = "60"
    solution_html = (
        "<p>Высота равнобедренного треугольника является медианой, поэтому</p>"
        '<center><p><span data-inline-latex="'
        + rf"AH=\frac{{AB}}{{2}}={_latex_number(half_base)}"
        + '"></span>.</p></center>'
        '<p>В прямоугольном <span data-inline-latex="\\triangle AHC"></span> '
        'по теореме Пифагора</p><center><p><span data-inline-latex="'
        + rf"AC=\sqrt{{AH^{{2}}+CH^{{2}}}}=\sqrt{{({_latex_number(half_base)})^{{2}}+({height_latex})^{{2}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
        '<p>Получили <span data-inline-latex="AC=BC=AB"></span>, поэтому '
        'треугольник <span data-inline-latex="ABC"></span> равносторонний и '
        '<span data-inline-latex="\\angle C=60^{\\circ}"></span>.</p>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27795_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-vertex-angle-to-altitude repair for 27795."""

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
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("vertex angle must form a triangle")
    sine = sp.simplify(sp.sin(sp.pi * angle / 180))
    if sine.has(sp.sin):
        raise IsoscelesTrianglePlanError("vertex angle has no supported exact sine")
    height = sp.simplify(side * sine)
    answer = _answer_text(height)
    solution_html = (
        '<p>В прямоугольном <span data-inline-latex="\\triangle AHC"></span> '
        'высота <span data-inline-latex="AH"></span> является катетом, противолежащим углу '
        '<span data-inline-latex="C"></span>. Поэтому</p><center><p><span data-inline-latex="'
        + rf"AH=AC\sin \angle C={side_latex}\sin {angle}^{{\circ}}={side_latex}\cdot {_latex_number(sine)}={_latex_number(height)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27796_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-altitude-to-acute-angle repair for 27796."""

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
    if not re.search(r"остро.*уголь", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare an acute triangle")
    side_match = re.search(r"\bAC\s*=\s*BC\s*=\s*([^,;.]+)", formula)
    height_match = re.search(
        r"высот[^.]*\bAH\b\s+равна\s*([^,;.]+)", formula, re.IGNORECASE
    )
    if side_match is None or height_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and altitude AH")
    if not re.search(
        r"угол\s+C\b|градус[^.]*угла\s+C\b",
        _request_text(condition_html),
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError("condition must request angle C")
    side_latex = side_match.group(1).strip()
    height_latex = height_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    height = _parse_positive_value(height_latex)
    ratio = sp.simplify(height / side)
    if ratio >= 1:
        raise IsoscelesTrianglePlanError("altitude must be shorter than the equal side")
    angle = sp.simplify(180 * sp.asin(ratio) / sp.pi)
    if angle.has(sp.asin) or angle.is_rational is not True:
        raise IsoscelesTrianglePlanError(
            "altitude ratio has no supported exact acute angle"
        )
    answer = _answer_text(angle)
    solution_html = (
        '<p>В прямоугольном <span data-inline-latex="\\triangle AHC"></span> '
        '<span data-inline-latex="AC"></span> — гипотенуза. По определению синуса</p>'
        '<center><p><span data-inline-latex="'
        + rf"\sin \angle C=\frac{{AH}}{{AC}}=\frac{{{height_latex}}}{{{side_latex}}}={_latex_number(ratio)}"
        + '"></span>,</p></center><p>откуда, так как угол <span data-inline-latex="C"></span> острый,</p>'
        '<center><p><span data-inline-latex="'
        + rf"\angle C={_latex_number(angle)}^{{\circ}}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )
