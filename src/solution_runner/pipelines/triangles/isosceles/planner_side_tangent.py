"""Build exact isosceles side-length repairs for audited profiles."""

from __future__ import annotations

import re
from typing import Any

import sympy as sp

from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def build_group_27288_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build only the equal-side-and-tangent to base repair for group 27288."""

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
    tangent_latex = _inline_assignment(condition_html, r"\\tg\s*A\s*=")
    side = _parse_positive_value(side_match.group(1))
    tangent = _parse_positive_value(tangent_latex)
    cosine = sp.sqrt(sp.simplify(1 / (1 + tangent**2)))
    answer = _answer_text(2 * side * cosine)
    solution_html = (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Следовательно,</p><center><p><span data-inline-latex="'
        r"AB=2AH=2AC\cos A=2AC\sqrt{\frac{1}{1+\tg^{2} A}}="
        rf"2\cdot {_latex_number(side)}\cdot "
        rf"\sqrt{{\frac{{1}}{{1+({tangent_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
        + '"></span>.</p></center>'
    )
    return _build_missing_solution_plan(
        content,
        answer=answer,
        solution_html=solution_html,
        parent_condition_asset_id=parent_condition_asset_id,
    )


def build_group_27289_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
    parent_solution_assets: tuple[dict[str, str], ...],
) -> RepairPlan:
    """Build only the base-and-tangent to equal-side repair for group 27289."""

    from .planner import (
        _answer_matches,
        _answer_text,
        _asset_transformation,
        _formula_text,
        _inline_assignment,
        _inline_formulas,
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
        r"\d+(?:\{,\}\d+)?)",
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
    tangent_latex = _inline_assignment(condition_html, r"\\tg\s*A\s*=")
    base = _parse_positive_value(base_latex)
    tangent = _parse_positive_value(tangent_latex)
    cosine = sp.sqrt(sp.simplify(1 / (1 + tangent**2)))
    answer = _answer_text(base / (2 * cosine))
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    transformations: list[dict[str, Any]] = []
    if solution_missing:
        if len(parent_solution_assets) != 1:
            raise IsoscelesTrianglePlanError(
                "group 27289 parent must provide one solution asset"
            )
        current_condition_asset = next(
            (
                item
                for item in content.get("assets", [])
                if isinstance(item, dict) and item.get("asset_key") == "image_1"
            ),
            None,
        )
        if (
            not isinstance(current_condition_asset, dict)
            or current_condition_asset.get("asset_id") != parent_condition_asset_id
        ):
            transformations.append(_asset_transformation(parent_condition_asset_id))
        solution_asset = parent_solution_assets[0]
        solution_asset_transformation = _solution_asset_transformation(
            solution_asset,
            expected_asset_key="image_2",
        )
        image_html = str(solution_asset_transformation["value"]["html"])
        solution_html = (
            image_html + '<p>Треугольник <span data-inline-latex="ABC"></span> — '
            'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
            'делит основание <span data-inline-latex="AB"></span> пополам. '
            'Тогда</p><center><p><span data-inline-latex="'
            r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}="
            r"\frac{AB}{2\sqrt{\frac{1}{1+\tg^{2} A}}}="
            rf"\frac{{{_latex_number(base)}}}{{2\sqrt{{\frac{{1}}{{1+({tangent_latex})^{{2}}}}}}}}="
            + answer.replace(",", "{,}")
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
        transformations.append(solution_asset_transformation)
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
