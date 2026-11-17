"""Build audited isosceles-triangle content repairs."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27799_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the base-and-included-angle-to-equal-side repair for 27799."""

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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|\^\\circ|°)",
        formula,
        re.IGNORECASE,
    )
    base_match = re.search(r"\bAB\s*=\s*(.+?)(?=\s+Найд|[,;.]|$)", formula)
    if angle_match is None or base_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C and base AB")
    request = _request_text(condition_html)
    if not re.search(r"\bAC\b", request) or re.search(
        r"\b(?:AB|BC|AH|BH|CH)\b", request
    ):
        raise IsoscelesTrianglePlanError("condition must request AC")
    angle = int(angle_match.group(1))
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("included angle must form a triangle")
    base_latex = base_match.group(1).strip()
    base = _parse_positive_value(base_latex)
    cosine = sp.simplify(sp.cos(sp.pi * angle / 180))
    if cosine.has(sp.cos):
        raise IsoscelesTrianglePlanError("included angle has no supported exact cosine")
    denominator = sp.simplify(2 * (1 - cosine))
    side = sp.simplify(base / sp.sqrt(denominator))
    answer = _answer_text(side)
    solution_html = (
        "<p>По теореме косинусов и с учётом "
        '<span data-inline-latex="AC=BC"></span>:</p><center><p><span data-inline-latex="'
        + r"AB^{2}=AC^{2}+BC^{2}-2AC\cdot BC\cos \angle C=2AC^{2}\left(1-\cos \angle C\right)"
        + '"></span>.</p></center><p>Следовательно,</p><center><p><span data-inline-latex="'
        + r"AC=\sqrt{\frac{AB^{2}}{2\left(1-\cos \angle C\right)}}"
        + rf"=\sqrt{{\frac{{({base_latex})^{{2}}}}{{{_latex_number(denominator)}}}}}={_latex_number(side)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
    )


def build_group_27800_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-included-angle-to-base repair for 27800."""

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
    if not re.search(r"\bAC\s*=\s*BC\b", formula):
        raise IsoscelesTrianglePlanError("condition must declare AC=BC")
    angle_match = re.search(
        r"угол\s+C\s+равен\s*(\d+)\s*(?:\^\{?\\circ\}?|\^\\circ|°)",
        formula,
        re.IGNORECASE,
    )
    side_match = re.search(
        r"\bAC\s*=\s*(?!\s*BC\b)(.+?)(?=\s+Найд|[,;.]|$)",
        formula,
    )
    if angle_match is None or side_match is None:
        raise IsoscelesTrianglePlanError("condition must give angle C and side AC")
    request = _request_text(condition_html)
    if not re.search(r"\bAB\b", request) or re.search(
        r"\b(?:AC|BC|AH|BH|CH)\b", request
    ):
        raise IsoscelesTrianglePlanError("condition must request AB")
    angle = int(angle_match.group(1))
    if angle <= 0 or angle >= 180:
        raise IsoscelesTrianglePlanError("included angle must form a triangle")
    side_latex = side_match.group(1).strip()
    side = _parse_positive_value(side_latex)
    cosine = sp.simplify(sp.cos(sp.pi * angle / 180))
    if cosine.has(sp.cos):
        raise IsoscelesTrianglePlanError("included angle has no supported exact cosine")
    factor = sp.simplify(2 * (1 - cosine))
    base = sp.simplify(side * sp.sqrt(factor))
    side_squared = sp.simplify(side**2)
    base_squared = sp.simplify(base**2)
    cross_term = sp.simplify(-2 * side_squared * cosine)
    cross_operator = "+" if cross_term >= 0 else "-"
    cross_term_latex = _latex_number(abs(cross_term))
    answer = _answer_text(base)
    solution_html = (
        "<p>Найдём косинус данного угла:</p>"
        '<center><p><span data-inline-latex="'
        + rf"\cos \angle C=\cos {angle}^{{\circ}}={_latex_number(cosine)}"
        + '"></span>.</p></center>'
        "<p>По теореме косинусов:</p>"
        '<center><p><span data-inline-latex="'
        + r"AB^{2}=AC^{2}+BC^{2}-2AC\cdot BC\cos \angle C"
        + '"></span>.</p></center>'
        '<p>Так как <span data-inline-latex="AC=BC='
        + side_latex
        + '"></span>, подставим известные значения и последовательно выполним вычисления:</p>'
        '<center><p><span data-inline-latex="'
        + rf"AB^{{2}}=({side_latex})^{{2}}+({side_latex})^{{2}}"
        + rf"-2\cdot({side_latex})\cdot({side_latex})\cdot({_latex_number(cosine)})"
        + rf"\iff AB^{{2}}={_latex_number(side_squared)}+{_latex_number(side_squared)}"
        + rf"-2\cdot {_latex_number(side_squared)}\cdot({_latex_number(cosine)})"
        + rf"\iff AB^{{2}}={_latex_number(side_squared)}+{_latex_number(side_squared)}"
        + rf"{cross_operator}{cross_term_latex}"
        + rf"\iff AB^{{2}}={_latex_number(base_squared)}"
        + '"></span>.</p></center>'
        "<p>Длина стороны положительна, поэтому</p>"
        '<center><p><span data-inline-latex="'
        + rf"AB=\sqrt{{{_latex_number(base_squared)}}}={_latex_number(base)}"
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
        ensure_condition_asset=True,
        refresh_solution=True,
    )


def build_group_628232_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the equal-side-and-tangent to base repair for group 628232."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _asset_transformation,
        _formula_text,
        _inline_assignment,
        _latex_number,
        _normalized_content,
        _parse_positive_value,
        _plain_html,
        _request_text,
        _section,
        _section_transformation,
        _solution_asset_transformation,
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
    side_match = re.search(
        r"(?:AC\s*=\s*BC|BC\s*=\s*AC)\s*=\s*"
        r"((?:\d+(?:\{,\}\d+|[.,]\d+)?)?\\sqrt\{\d+\}|"
        r"\d+(?:\{,\}\d+|[.,]\d+)?)",
        formula,
    )
    if side_match is None:
        raise IsoscelesTrianglePlanError("condition must give AC=BC and their length")
    tangent_latex = _inline_assignment(condition_html, r"\\tg\s*\\angle\s*A\s*=")
    request = _request_text(condition_html)
    if not re.search(r"\bAB\b", request) or re.search(
        r"\b(?:AC|BC|AH|BH|CH)\b", request
    ):
        raise IsoscelesTrianglePlanError("condition must request AB")
    side_latex = side_match.group(1)
    side = _parse_positive_value(side_latex)
    tangent = _parse_positive_value(tangent_latex)
    half_base = sp.simplify(side / sp.sqrt(1 + tangent**2))
    base = sp.simplify(2 * half_base)
    answer = _answer_text(base)
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations: list[dict[str, Any]] = []
    if solution_missing:
        solution_images = [
            item
            for item in parent_solution_assets
            if item.get("asset_key") == "image_2"
        ]
        if len(solution_images) != 1:
            raise IsoscelesTrianglePlanError(
                "group 628232 parent must provide one solution image_2"
            )
        transformations.append(_asset_transformation(parent_condition_asset_id))
        solution_asset = _solution_asset_transformation(
            solution_images[0], expected_asset_key="image_2"
        )
        image_html = str(solution_asset["value"]["html"])
        solution_html = (
            image_html + '<p>Проведём высоту <span data-inline-latex="CH"></span>. '
            'Так как треугольник <span data-inline-latex="ABC"></span> '
            'равнобедренный, <span data-inline-latex="AH=HB"></span>. Пусть '
            '<span data-inline-latex="AH=x"></span>. По определению тангенса</p>'
            '<center><p><span data-inline-latex="'
            + rf"\tg \angle A=\frac{{CH}}{{AH}}={tangent_latex}"
            + rf"\iff CH={tangent_latex}x"
            + '"></span>.</p></center>'
            '<p>По теореме Пифагора для <span data-inline-latex="\\triangle ACH"></span>:</p>'
            '<center><p><span data-inline-latex="'
            + r"AC^{2}=AH^{2}+CH^{2}"
            + rf"\iff ({side_latex})^{{2}}=x^{{2}}+({tangent_latex}x)^{{2}}"
            + rf"\iff x={_latex_number(half_base)}"
            + '"></span>.</p></center>'
            '<p>Следовательно,</p><center><p><span data-inline-latex="'
            + rf"AB=2AH=2\cdot {_latex_number(half_base)}={_latex_number(base)}"
            + '"></span>.</p></center>'
        )
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
                asset_keys=("image_2",),
            )
        )
        transformations.append(solution_asset)
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
