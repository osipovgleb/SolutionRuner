"""Build audited isosceles height and projection repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27330_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the altitude-and-side to base-angle sine repair for 27330."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _condition_image_repairs,
        _formula_text,
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
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    first_orientation = re.search(r"\bAC\s*=\s*BC\b", formula) is not None
    second_orientation = re.search(r"\bAB\s*=\s*BC\b", formula) is not None
    if first_orientation == second_orientation:
        raise IsoscelesTrianglePlanError("condition must give exactly AC=BC or AB=BC")
    base_name = "AB" if first_orientation else "AC"
    altitude_name = "AH" if first_orientation else "CH"
    requested_angle = "A" if first_orientation else "C"
    long_angle = "BAC" if first_orientation else "ACB"
    base_match = re.search(rf"\b{base_name}\s*=\s*{number}", formula)
    altitude_match = re.search(
        rf"\b{altitude_name}\s*(?:=|равна)\s*{number}",
        formula,
        re.IGNORECASE,
    )
    if base_match is None or altitude_match is None:
        raise IsoscelesTrianglePlanError(
            f"condition must give {base_name} and altitude {altitude_name}"
        )
    request = _request_text(condition_html)
    if not re.search(
        rf"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?(?:{requested_angle}|{long_angle})\b",
        request,
        re.IGNORECASE,
    ):
        raise IsoscelesTrianglePlanError(
            f"condition must request sin {requested_angle}"
        )
    base_latex = base_match.group(1)
    altitude_latex = altitude_match.group(1)
    base = _parse_positive_value(base_latex)
    altitude = _parse_positive_value(altitude_latex)
    sine = sp.simplify(altitude / base)
    if sp.simplify(1 - sine).is_positive is not True:
        raise IsoscelesTrianglePlanError(
            f"{altitude_name} must be less than {base_name}"
        )
    answer = _answer_text(sine)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27330")
        if first_orientation
        else ()
    )
    if solution_missing:
        relation = (
            r"\sin \angle BAC=\sin \angle ABH=\frac{AH}{AB}="
            if first_orientation
            else r"\sin \angle ACB=\sin \angle BAC=\frac{CH}{AC}="
        )
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            "равнобедренный, поэтому углы при его основании равны. Тогда</p>"
            '<center><p><span data-inline-latex="'
            + relation
            + rf"\frac{{{_latex_number(altitude)}}}{{{_latex_number(base)}}}="
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


def build_group_27331_repair_plan(
    context: dict[str, Any],
    *,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the altitude-and-side to base-angle cosine repair for 27331."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _condition_image_repairs,
        _formula_text,
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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    number = r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|\d+(?:\{,\}\d+|[.,]\d+)?)"
    base_match = re.search(rf"\bAB\s*=\s*{number}", formula)
    altitude_match = re.search(
        rf"\bAH\s*(?:=|равна)\s*{number}", formula, re.IGNORECASE
    )
    projection_match = re.search(rf"\bBH\s*=\s*{number}", formula)
    cosine_variant = base_match is not None and projection_match is None
    sine_variant = base_match is None and projection_match is not None
    if altitude_match is None or cosine_variant == sine_variant:
        raise IsoscelesTrianglePlanError(
            "condition must give AH and exactly one of AB or BH"
        )
    request = _request_text(condition_html)
    altitude = _parse_positive_value(altitude_match.group(1))
    if cosine_variant:
        if not re.search(
            r"(?:косинус(?:\s+угла)?|\\cos)\s*(?:\\angle\s*)?(?:A|BAC)\b",
            request,
            re.IGNORECASE,
        ):
            raise IsoscelesTrianglePlanError("AB/AH variant must request cos A")
        base = _parse_positive_value(base_match.group(1))
        projection_squared = sp.simplify(base**2 - altitude**2)
        if projection_squared.is_positive is not True:
            raise IsoscelesTrianglePlanError("AH must be less than AB")
        projection = sp.sqrt(projection_squared)
        answer_value = sp.simplify(projection / base)
    else:
        if not re.search(
            r"(?:синус(?:\s+угла)?|\\sin)\s*(?:\\angle\s*)?(?:A|BAC)\b",
            request,
            re.IGNORECASE,
        ):
            raise IsoscelesTrianglePlanError("AH/BH variant must request sin A")
        projection = _parse_positive_value(projection_match.group(1))
        base = sp.sqrt(altitude**2 + projection**2)
        answer_value = sp.simplify(altitude / base)
    answer = _answer_text(answer_value)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations = list(
        _condition_image_repairs(content, parent_solution_assets, group_key="27331")
    )
    if solution_missing:
        base_latex = _latex_number(base)
        altitude_latex = _latex_number(altitude)
        projection_latex = _latex_number(projection)
        relation = (
            r"\cos \angle BAC=\cos \angle ABH=\frac{BH}{AB}="
            r"\frac{\sqrt{AB^{2}-AH^{2}}}{AB}="
            + rf"\frac{{\sqrt{{({base_latex})^{{2}}-({altitude_latex})^{{2}}}}}}{{{base_latex}}}="
            + rf"\frac{{{projection_latex}}}{{{base_latex}}}="
            if cosine_variant
            else r"AB=\sqrt{AH^{2}+BH^{2}}="
            + rf"\sqrt{{({altitude_latex})^{{2}}+({projection_latex})^{{2}}}}={base_latex},\quad "
            + r"\sin \angle BAC=\sin \angle ABH=\frac{AH}{AB}="
            + rf"\frac{{{altitude_latex}}}{{{base_latex}}}="
        )
        solution_html = (
            '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            "равнобедренный, поэтому углы при его основании равны. Тогда</p>"
            '<center><p><span data-inline-latex="'
            + relation
            + answer.replace(",", "{,}")
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(solution, "solution", "Решение", solution_html)
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
