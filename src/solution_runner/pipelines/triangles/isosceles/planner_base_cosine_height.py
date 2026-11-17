"""Build audited isosceles height and projection repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27322_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-cosine to opposite-side altitude repair for 27322."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _condition_image_repairs,
        _formula_text,
        _inline_formulas,
        _latex_number,
        _normalized_content,
        _parse_positive_value,
        _plain_html,
        _request_text,
        _section,
        _section_transformation,
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
    equal_match = re.search(r"\b(AB|AC|BC)\s*=\s*(AB|AC|BC)\b", formula)
    if equal_match is None or equal_match.group(1) == equal_match.group(2):
        raise IsoscelesTrianglePlanError("condition must state two equal sides")
    base_candidates = {"AB", "AC", "BC"} - {
        equal_match.group(1),
        equal_match.group(2),
    }
    if len(base_candidates) != 1:
        raise IsoscelesTrianglePlanError("equal sides do not determine one base")
    base_name = next(iter(base_candidates))
    base_vertices = set(base_name)
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(rf"{base_name}\s*=", item)
    ]
    visible_base = re.search(
        rf"\b{base_name}\s*=\s*((?:\d+(?:\{{,\}}\d+|[.,]\d+)?)?"
        r"\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one base length")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?[ABC]{3}\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError(
            "condition must give one cosine of a named base angle"
        )
    cosine_match = re.match(
        r"\\cos\s*(?:\\angle\s*)?([ABC]{3})\s*=\s*(.+)",
        cosine_assignments[0],
    )
    if cosine_match is None:
        raise IsoscelesTrianglePlanError("cosine assignment is malformed")
    angle_name, cosine_latex = cosine_match.groups()
    angle_vertex = angle_name[1]
    if angle_vertex not in base_vertices:
        raise IsoscelesTrianglePlanError("given angle must be a base angle")
    request = _request_text(condition_html)
    if re.findall(r"\b([ABC]H)\b", request) != [f"{angle_vertex}H"]:
        raise IsoscelesTrianglePlanError(
            "condition must request the altitude from the given base-angle vertex"
        )
    base = _parse_positive_value(base_latex)
    cosine = _parse_positive_value(cosine_latex)
    sine_squared = sp.simplify(1 - cosine**2)
    if sine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    sine = sp.sqrt(sine_squared)
    answer = _answer_text(base * sine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27322")
    )
    if solution_missing:
        other_base_vertex = next(iter(base_vertices - {angle_vertex}))
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            "равнобедренный, поэтому углы при его основании равны. Тогда</p>"
            '<center><p><span data-inline-latex="'
            + f"{angle_vertex}H={base_name}\\sin \\angle "
            + f"{angle_vertex}{other_base_vertex}H={base_name}\\sin \\angle {angle_name}="
            + f"{base_name}\\sqrt{{1-\\cos^{{2}} \\angle {angle_name}}}="
            + rf"{_latex_number(base)}\sqrt{{1-({cosine_latex})^{{2}}}}="
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )
    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        transformations.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))


def build_group_27323_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the direct base-cosine projection repair for group 27323."""

    from .planner import (
        _answer_text,
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
    if re.search(r"\bAC\s*=\s*BC\b", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    if not re.search(r"\bAH\b[^.]*высот|высот[^.]*\bAH\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError("condition must declare AH as altitude")
    request = _request_text(condition_html)
    if re.findall(r"\b([ABC]H)\b", request) != ["BH"]:
        raise IsoscelesTrianglePlanError("condition must request BH")
    inline_bases = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    visible_base = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_bases[0]
        if len(inline_bases) == 1
        else visible_base.group(1)
        if not inline_bases and visible_base is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give exactly one AB length")
    cosine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\cos\s*(?:\\angle\s*)?BAC\s*=", item)
    ]
    if len(cosine_assignments) != 1:
        raise IsoscelesTrianglePlanError("condition must give exactly cos BAC")
    cosine_latex = cosine_assignments[0].split("=", 1)[1].strip()
    base = _parse_positive_value(base_latex)
    cosine = _parse_positive_value(cosine_latex)
    if cosine >= 1:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(base * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        "равнобедренный, поэтому углы при его основании равны. Тогда</p>"
        '<center><p><span data-inline-latex="'
        r"BH=AB\cos \angle ABH=AB\cos \angle BAC="
        + rf"{_latex_number(base)}\cdot {cosine_latex}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
