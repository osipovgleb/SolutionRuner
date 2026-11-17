"""Build exact isosceles side-length repairs for audited profiles."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27285_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the AB-and-sine to equal-side repair used by group 27285."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _asset_transformation,
        _group_27285_solution_html,
        _parse_equal_side_from_base_and_sine,
        _plain_html,
        _section,
        _section_transformation,
    )

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise IsoscelesTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    base, sine, sine_latex = _parse_equal_side_from_base_and_sine(
        str(condition.get("html") or "")
    )
    answer = _answer_text(base / (2 * sp.sqrt(sp.simplify(1 - sine**2))))
    transformations: list[dict[str, Any]] = []
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    if (
        not isinstance(current_asset, dict)
        or current_asset.get("asset_id") != parent_condition_asset_id
    ):
        transformations.append(_asset_transformation(parent_condition_asset_id))
    solution = _section(content, "solution")
    if solution is None or not _plain_html(str(solution.get("html") or "")):
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                _group_27285_solution_html(base, sine, sine_latex, answer),
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


def build_group_27286_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-cosine to base repair for group 27286."""

    from .planner import (
        _answer_text,
        _build_missing_solution_plan,
        _formula_text,
        _inline_assignment,
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
    requested = _request_text(condition_html)
    if not re.search(r"\bAB\b", requested) or re.search(
        r"\b(?:AC|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AB")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    side_match = re.search(
        r"(?:AC\s*=\s*BC|BC\s*=\s*AC)\s*=\s*"
        r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC")
    cosine_latex = _inline_assignment(condition_html, r"\\cos\s*A\s*=")
    side = _parse_positive_value(side_match.group(1))
    cosine = _parse_positive_value(cosine_latex)
    if cosine >= 1:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(2 * side * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Тогда</p><center><p><span data-inline-latex="'
        rf"AB=2AH=2AC\cos A=2\cdot {_latex_number(side)}\cdot "
        + cosine_latex
        + "="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27287_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-cosine to equal-side repair for group 27287."""

    from .planner import (
        _answer_text,
        _build_missing_solution_plan,
        _formula_text,
        _inline_assignment,
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
    requested = _request_text(condition_html)
    if not re.search(r"\bAC\b", requested) or re.search(
        r"\b(?:AB|BC|AH|BH|CH)\b", requested
    ):
        raise IsoscelesTrianglePlanError("condition must request AC")
    formula = (
        _formula_text(condition_html)
        .replace("А", "A")
        .replace("В", "B")
        .replace("С", "C")
    )
    if re.search(r"(?:AC\s*=\s*BC|BC\s*=\s*AC)", formula) is None:
        raise IsoscelesTrianglePlanError("condition must state AC=BC")
    inline_base = [
        item.split("=", 1)[1].strip()
        for item in _inline_formulas(condition_html)
        if re.match(r"AB\s*=", item)
    ]
    base_match = re.search(
        r"\bAB\s*=\s*((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    base_latex = (
        inline_base[0]
        if len(inline_base) == 1
        else base_match.group(1)
        if not inline_base and base_match is not None
        else ""
    )
    if not base_latex:
        raise IsoscelesTrianglePlanError("condition must give AB")
    cosine_latex = _inline_assignment(condition_html, r"\\cos\s*A\s*=")
    base = _parse_positive_value(base_latex)
    cosine = _parse_positive_value(cosine_latex)
    if cosine >= 1:
        raise IsoscelesTrianglePlanError("base-angle cosine must be less than one")
    answer = _answer_text(base / (2 * cosine))
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Тогда</p><center><p><span data-inline-latex="'
        r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}="
        rf"\frac{{{_latex_number(base)}}}{{2\cdot {cosine_latex}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )
