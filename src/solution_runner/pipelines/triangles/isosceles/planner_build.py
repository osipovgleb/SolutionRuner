"""Build and validate reusable isosceles-triangle repair plans."""

from __future__ import annotations

from typing import Any

import sympy as sp
from bs4 import BeautifulSoup

from .planner_parse import _answer_text, _latex_number, _parse_base_from_sine
from .planner_transforms import (
    _asset_transformation,
    _plain_html,
    _section,
    _section_transformation,
    _without_asset_markup,
)
from .planner_types import IsoscelesTrianglePlanError, RepairPlan


def _solution_html(
    side: sp.Expr,
    angle: str,
    sine: sp.Expr,
    sine_latex: str,
    answer: str,
) -> str:
    """Adapt the selected parent solution while preserving its proof shape."""

    cosine = sp.sqrt(sp.simplify(1 - sine**2))
    side_latex = _latex_number(side)
    cosine_latex = _latex_number(cosine)
    answer_latex = answer.replace(",", "{,}")
    formula = (
        rf"AB=2AH=2AC\cos {angle}=2AC\sqrt{{1-\sin^{{2}} {angle}}}="
        rf"2\cdot {side_latex}\sqrt{{1-({sine_latex})^{{2}}}}="
        rf"{_latex_number(2 * side)}\cdot {cosine_latex}={answer_latex}"
    )
    return (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Следовательно,</p><center><p><span data-inline-latex="'
        + formula
        + '"></span>.</p></center>'
    )


def _group_27285_solution_html(
    base: sp.Expr,
    sine: sp.Expr,
    sine_latex: str,
    answer: str,
) -> str:
    """Adapt the inverse parent proof for the exact group-27285 contract."""

    formula = (
        r"AC=\frac{AH}{\cos A}=\frac{AB}{2\cos A}="
        r"\frac{AB}{2\sqrt{1-\sin^{2} A}}="
        rf"\frac{{{_latex_number(base)}}}{{2\sqrt{{1-({sine_latex})^{{2}}}}}}="
        + answer.replace(",", "{,}")
    )
    return (
        '<p>Треугольник <span data-inline-latex="ABC"></span> — '
        'равнобедренный, поэтому высота <span data-inline-latex="CH"></span> '
        'делит основание <span data-inline-latex="AB"></span> пополам. '
        'Тогда</p><center><p><span data-inline-latex="'
        + formula
        + '"></span>.</p></center>'
    )


def _build_missing_solution_plan(
    content: dict[str, Any],
    *,
    answer: str,
    solution_html: str,
    parent_condition_asset_id: str,
    ensure_condition_asset: bool = False,
    refresh_solution: bool = False,
) -> RepairPlan:
    """Build shared minimal writes after one group-specific proof is solved."""

    transformations: list[dict[str, Any]] = []
    solution = _section(content, "solution")
    solution_missing = solution is None or not _plain_html(
        str(solution.get("html") or "")
    )
    solution_needs_write = solution_missing or (
        refresh_solution
        and solution is not None
        and str(solution.get("html") or "") != solution_html
    )
    condition = _section(content, "condition")
    if condition is None:
        raise IsoscelesTrianglePlanError("condition section is required")
    current_asset = next(
        (
            item
            for item in content.get("assets", [])
            if isinstance(item, dict) and item.get("asset_key") == "image_1"
        ),
        None,
    )
    solution_has_image = solution is not None and (
        "image_1" in tuple(str(value) for value in solution.get("asset_keys", []))
        or BeautifulSoup(str(solution.get("html") or ""), "html.parser").find(
            "img", attrs={"data-asset-key": "image_1"}
        )
        is not None
    )
    condition_keys = tuple(str(value) for value in condition.get("asset_keys", []))
    condition_has_image = "image_1" in condition_keys and bool(
        BeautifulSoup(str(condition.get("html") or ""), "html.parser").find(
            "img", attrs={"data-asset-key": "image_1"}
        )
    )
    condition_asset_repair = (
        ensure_condition_asset or solution_missing or solution_has_image
    ) and (
        not condition_has_image
        or not isinstance(current_asset, dict)
        or current_asset.get("asset_id") != parent_condition_asset_id
    )
    if solution is not None and solution_has_image and not solution_needs_write:
        cleaned_html, remaining_keys = _without_asset_markup(solution, "image_1")
        transformations.append(
            _section_transformation(
                solution,
                "solution",
                str(solution.get("title") or "Решение"),
                cleaned_html,
                asset_keys=remaining_keys,
            )
        )
    if condition_asset_repair:
        transformations.append(_asset_transformation(parent_condition_asset_id))
    if solution_needs_write:
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


def _normalized_content(context: dict[str, Any]) -> dict[str, Any]:
    """Return one validated schema-v3 normalized content object."""

    content = context.get("normalized_content")
    if (
        not isinstance(content, dict)
        or content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise IsoscelesTrianglePlanError("schema-v3 Normalized content is required")
    return content


def _answer_matches(section: dict[str, Any] | None, expected: str) -> bool:
    """Return whether the current answer is numerically equal to expected."""

    if section is None:
        return False
    current = _plain_html(str(section.get("html") or "")).replace(" ", "")
    try:
        return sp.Rational(current.replace(",", ".")) == sp.Rational(
            expected.replace(",", ".")
        )
    except (TypeError, ValueError):
        return False


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
) -> RepairPlan:
    """Build the minimal group-27284 repair and preserve existing solutions."""

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
    side, angle, sine, sine_latex = _parse_base_from_sine(
        str(condition.get("html") or "")
    )
    answer = _answer_text(2 * side * sp.sqrt(sp.simplify(1 - sine**2)))
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
                _solution_html(side, angle, sine, sine_latex, answer),
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
