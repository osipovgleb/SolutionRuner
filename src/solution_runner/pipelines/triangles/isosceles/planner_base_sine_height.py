"""Build audited isosceles height and projection repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def _parse_27320(condition_html):
    from .planner import (
        _formula_text,
        _inline_formulas,
        _parse_positive_value,
        _request_text,
    )

    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    equal_match = re.search(r"\b(AB|AC|BC)\s*=\s*(AB|AC|BC)\b", formula)
    if equal_match is None or equal_match.group(1) == equal_match.group(2):
        raise IsoscelesTrianglePlanError("condition must state two equal sides")
    equal_sides = {equal_match.group(1), equal_match.group(2)}
    all_sides = {"AB", "AC", "BC"}
    base_candidates = all_sides - equal_sides
    if len(base_candidates) != 1:
        raise IsoscelesTrianglePlanError("equal sides do not determine one base")
    base_name = next(iter(base_candidates))
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
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*[ABC]{3}\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError(
            "condition must give one sine of a named base angle"
        )
    sine_match = re.match(r"\\sin\s*([ABC]{3})\s*=\s*(.+)", sine_assignments[0])
    if sine_match is None:
        raise IsoscelesTrianglePlanError("sine assignment is malformed")
    angle_name, sine_latex = sine_match.groups()
    base_vertices = set(base_name)
    angle_vertex = angle_name[1]
    if angle_vertex not in base_vertices:
        raise IsoscelesTrianglePlanError("given angle must be a base angle")
    request = _request_text(condition_html)
    altitude_matches = re.findall(r"\b([ABC]H)\b", request)
    if altitude_matches != [f"{angle_vertex}H"]:
        raise IsoscelesTrianglePlanError(
            "condition must request the altitude from the given base-angle vertex"
        )
    base = _parse_positive_value(base_latex)
    sine = _parse_positive_value(sine_latex)
    if sine >= 1:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    return base_name, base_vertices, angle_name, angle_vertex, base, sine, sine_latex


def _parse_27321(condition_html):
    from .planner import (
        _formula_text,
        _inline_formulas,
        _parse_positive_value,
        _request_text,
    )

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
    sine_assignments = [
        item
        for item in _inline_formulas(condition_html)
        if re.match(r"\\sin\s*[ABC]{3}\s*=", item)
    ]
    if len(sine_assignments) != 1:
        raise IsoscelesTrianglePlanError(
            "condition must give one sine of a named base angle"
        )
    sine_match = re.match(r"\\sin\s*([ABC]{3})\s*=\s*(.+)", sine_assignments[0])
    if sine_match is None:
        raise IsoscelesTrianglePlanError("sine assignment is malformed")
    angle_name, sine_latex = sine_match.groups()
    angle_vertex = angle_name[1]
    if angle_vertex not in base_vertices:
        raise IsoscelesTrianglePlanError("given angle must be a base angle")
    other_base_vertex = next(iter(base_vertices - {angle_vertex}))
    if not re.search(
        rf"\b{angle_vertex}H\b[^.]*высот", formula, re.IGNORECASE
    ) and not re.search(rf"высот[^.]*\b{angle_vertex}H\b", formula, re.IGNORECASE):
        raise IsoscelesTrianglePlanError(
            "condition must declare the altitude from the given base-angle vertex"
        )
    request = _request_text(condition_html)
    if re.findall(r"\b([ABC]H)\b", request) != [f"{other_base_vertex}H"]:
        raise IsoscelesTrianglePlanError(
            "condition must request the adjacent projection segment"
        )
    base = _parse_positive_value(base_latex)
    sine = _parse_positive_value(sine_latex)
    cosine_squared = sp.simplify(1 - sine**2)
    if cosine_squared.is_positive is not True:
        raise IsoscelesTrianglePlanError("base-angle sine must be less than one")
    cosine = sp.sqrt(cosine_squared)
    return (
        base_name,
        other_base_vertex,
        angle_vertex,
        angle_name,
        base,
        cosine,
        sine_latex,
    )


def build_group_27320_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-sine to opposite-side altitude repair for 27320."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _condition_image_repairs,
        _latex_number,
        _normalized_content,
        _plain_html,
        _section,
        _section_transformation,
    )

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    base_name, base_vertices, angle_name, angle_vertex, base, sine, sine_latex = (
        _parse_27320(condition_html)
    )
    answer = _answer_text(base * sine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27320")
    )
    if solution_missing:
        other_base_vertex = next(iter(base_vertices - {angle_vertex}))
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            "равнобедренный, поэтому углы при его основании равны. Тогда</p>"
            '<center><p><span data-inline-latex="'
            + f"{angle_vertex}H={base_name}\\sin \\angle "
            + f"{angle_vertex}{other_base_vertex}H={base_name}\\sin \\angle {angle_name}="
            + rf"{_latex_number(base)}\cdot {sine_latex}="
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


def build_group_27321_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-sine to adjacent projection repair for 27321."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _condition_image_repairs,
        _latex_number,
        _normalized_content,
        _plain_html,
        _section,
        _section_transformation,
    )

    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    condition_html = str(condition.get("html") or "")
    base_name, other_base_vertex, angle_vertex, angle_name, base, cosine, sine_latex = (
        _parse_27321(condition_html)
    )
    answer = _answer_text(base * cosine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27321")
    )
    if solution_missing:
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            "равнобедренный, поэтому углы при его основании равны. Следовательно,</p>"
            '<center><p><span data-inline-latex="'
            + f"{other_base_vertex}H={base_name}\\cos \\angle "
            + f"{angle_vertex}{other_base_vertex}H={base_name}\\cos \\angle {angle_name}="
            + f"{base_name}\\sqrt{{1-\\sin^{{2}} \\angle {angle_name}}}="
            + rf"{_latex_number(base)}\sqrt{{1-({sine_latex})^{{2}}}}="
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
