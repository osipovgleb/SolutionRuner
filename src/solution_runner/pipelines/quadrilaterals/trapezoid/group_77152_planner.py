"""Isosceles-trapezoid leg from bases and sine for group 77152."""

from __future__ import annotations

from fractions import Fraction
from html import unescape
from math import isqrt
import re
from typing import Any

from ...triangles.isosceles.planner import _asset_transformation, _section_transformation
from ...triangles.right.planner import RepairPlan, RightTrianglePlanError

RULE = "trapezoid-77152-isosceles-leg-from-sine"


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    found = [s for s in content.get("sections", []) if isinstance(s, dict) and s.get("key") == key]
    if len(found) > 1:
        raise RightTrianglePlanError(f"multiple {key} sections")
    return found[0] if found else None


def _visible(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html))).replace("\u00ad", "").strip()


def _data(html: str) -> tuple[int, int, Fraction, Fraction, Fraction]:
    text = _visible(html)
    required = ("Основания равнобедренной трапеции равны", "Синус острого угла трапеции равен", "Найдите боковую сторону")
    if any(item not in text for item in required):
        raise RightTrianglePlanError("condition is outside frozen group-77152 grammar")
    bases = re.search(r"равны\s*(\d+)\s*и\s*(\d+)", text)
    sine = re.search(r"равен\s*(\d+(?:,\d+)?)\.\s*Найдите боковую", text)
    if bases is None or sine is None:
        raise RightTrianglePlanError("condition must state two bases and decimal sine")
    a, b = int(bases.group(1)), int(bases.group(2))
    sin_value = Fraction(sine.group(1).replace(",", "."))
    if a <= 0 or b <= 0 or a == b or not 0 < sin_value < 1:
        raise RightTrianglePlanError("inconsistent trapezoid values")
    squared = 1 - sin_value * sin_value
    n, d = isqrt(squared.numerator), isqrt(squared.denominator)
    if n * n != squared.numerator or d * d != squared.denominator:
        raise RightTrianglePlanError("unsupported irrational cosine")
    cosine = Fraction(n, d)
    return a, b, sin_value, cosine, Fraction(abs(a - b), 2) / cosine


def _decimal(value: Fraction, latex: bool = False) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    if value.denominator in {2, 5, 10}:
        output = f"{float(value):g}".replace(".", ",")
        return output.replace(",", "{,}") if latex else output
    raise RightTrianglePlanError("answer is not an integer or half-integer")


def _solution_matches(current: str, expected: str, asset_id: str) -> bool:
    if current == expected:
        return True
    suffix = (
        r'<img alt="" data-asset-id="' + re.escape(asset_id)
        + r'" data-asset-key="image_1" data-transformation-target-id="asset:image_1" '
        + r'src="/assets/' + re.escape(asset_id) + r'"/>'
    )
    return re.fullmatch(re.escape(expected) + suffix, current) is not None


def build_repair_plan(context: dict[str, Any], *, parent_condition_asset_id: str) -> RepairPlan:
    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    a, b, sine, cosine, leg = _data(str(condition.get("html") or ""))
    gap = abs(a - b)
    answer, latex_answer = _decimal(leg), _decimal(leg, True)
    sin_text, cos_text = _decimal(sine, True), _decimal(cosine, True)
    html = (
        f'<section data-content-kind="solution" data-content-rule="{RULE}" data-solution-title="Решение">'
        '<p>Проведём высоты трапеции. В равнобедренной трапеции отрезок у каждого края равен половине разности оснований:</p>'
        f'<center><p><span data-inline-latex="AH=\\frac{{|{a}-{b}|}}{{2}}=\\frac{{{gap}}}{{2}}"></span>.</p></center>'
        '<p>Из прямоугольного треугольника найдём косинус острого угла:</p>'
        f'<center><p><span data-inline-latex="\\cos \\angle BAD=\\sqrt{{1-\\sin^2 \\angle BAD}}=\\sqrt{{1-{sin_text}^2}}={cos_text}"></span>.</p></center>'
        '<p>Тогда боковая сторона равна:</p>'
        f'<center><p><span data-inline-latex="AB=\\frac{{AH}}{{\\cos \\angle BAD}}=\\frac{{{gap}}}{{2\\cdot {cos_text}}}={latex_answer}"></span>.</p></center></section>'
    )
    changes: list[dict[str, Any]] = []
    solution = _section(content, "solution")
    keys = tuple(str(key) for key in (solution or {}).get("asset_keys", []))
    if solution is None or not _solution_matches(str(solution.get("html") or ""), html, parent_condition_asset_id) or keys:
        changes.append(_section_transformation(solution, "solution", "Решение", html))
    if parent_condition_asset_id not in str(condition.get("html") or ""):
        changes.append(_asset_transformation(parent_condition_asset_id))
    answer_section = _section(content, "answer")
    answer_html = f'<p><span data-effect="spaced">{answer}</span></p>'
    if answer_section is None or str(answer_section.get("html") or "") != answer_html:
        changes.append(_section_transformation(answer_section, "answer", "Ответ", answer_html))
    return RepairPlan(answer=answer, transformations=tuple(changes))
