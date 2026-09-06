"""Strict, expanded sine repair for the two-task group 642289."""

from __future__ import annotations

from fractions import Fraction
from html import unescape
import re
from typing import Any

from .planner import RepairPlan, RightTrianglePlanError


RULE = "right-triangle-642289-sine-opposite"


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    matches = [
        value for value in content.get("sections", [])
        if isinstance(value, dict) and value.get("key") == key
    ]
    if len(matches) > 1:
        raise RightTrianglePlanError(f"multiple {key} sections")
    return matches[0] if matches else None


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(value))).replace("\u00ad", "").strip()


def _number(value: str, *, label: str) -> Fraction:
    compact = value.replace("{,}", ".").replace(",", ".")
    if not re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d+)?", compact):
        raise RightTrianglePlanError(f"{label} must be a positive decimal")
    parsed = Fraction(compact)
    if parsed <= 0:
        raise RightTrianglePlanError(f"{label} must be positive")
    return parsed


def _latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    scale = 1
    while scale < 1_000_000 and scale % value.denominator:
        scale *= 10
    if scale % value.denominator == 0:
        whole, remainder = divmod(value.numerator, value.denominator)
        digits = str(remainder * (scale // value.denominator)).zfill(len(str(scale)) - 1)
        return (f"{whole}.{digits}").rstrip("0").rstrip(".").replace(".", "{,}")
    return rf"\frac{{{value.numerator}}}{{{value.denominator}}}"


def _answer(value: Fraction) -> str:
    rendered = _latex(value)
    return rendered.replace("{,}", ",")


def _values(condition_html: str) -> tuple[Fraction, Fraction]:
    visible = _plain(condition_html)
    values = re.findall(r'data-inline-latex="([^"]+)"', unescape(condition_html))
    normalized = [value.replace(" ", "").replace(r"\angle", "") for value in values]
    trig = [value.removeprefix(r"\sinA=") for value in normalized if value.startswith(r"\sinA=")]
    if len(trig) != 1:
        raise RightTrianglePlanError("condition must declare exactly one sin A value")
    side = re.search(r"\bAB\s*=\s*([0-9]+(?:[,.][0-9]+)?)\b", visible)
    if side is None:
        raise RightTrianglePlanError("condition must declare AB as a positive decimal")
    required = ("В треугольнике ABC", "угол C", "90", "Найдите BC")
    if any(term not in visible for term in required):
        raise RightTrianglePlanError("condition is outside the frozen group-642289 grammar")
    sine = _number(trig[0], label="sin A")
    if sine >= 1:
        raise RightTrianglePlanError("sin A must be strictly below one")
    return _number(side.group(1), label="AB"), sine


def _asset(content: dict[str, Any], parent_asset_id: str) -> dict[str, Any] | None:
    images = [
        item for item in content.get("assets", [])
        if isinstance(item, dict) and item.get("kind") == "ordinary_image"
    ]
    matching = [item for item in images if item.get("asset_key") == "image_1"]
    if not matching:
        return {
            "transformation_target_id": "asset:image_1",
            "operation": "add",
            "value": {"parent_target_id": "section:condition:1", "position": 0,
                      "asset_key": "image_1", "asset_id": parent_asset_id,
                      "url": f"/assets/{parent_asset_id}", "kind": "ordinary_image", "alt": ""},
        }
    if len(images) != 1 or len(matching) != 1 or matching[0].get("asset_id") != parent_asset_id:
        raise RightTrianglePlanError("condition has a foreign or ambiguous image layout")
    return None


def _solution(ab: Fraction, sine: Fraction, result: Fraction, *, operation: str) -> dict[str, Any]:
    html = (
        f'<section data-content-kind="solution" data-content-rule="{RULE}" data-solution-title="Решение">'
        '<p>По определению синуса в прямоугольном треугольнике отношение противолежащего катета к гипотенузе равно синусу острого угла:</p>'
        '<center><p><span data-inline-latex="\\sin A=\\frac{BC}{AB}"></span>.</p></center>'
        '<p>Выразим искомый катет:</p>'
        '<center><p><span data-inline-latex="BC=AB\\cdot\\sin A"></span>.</p></center>'
        '<p>Подставим данные условия:</p>'
        f'<center><p><span data-inline-latex="BC={_latex(ab)}\\cdot{_latex(sine)}={_latex(result)}"></span>.</p></center>'
        '</section>'
    )
    return {"transformation_target_id": "section:solution", "operation": operation,
            "value": {"title": "Решение", "html": html, "asset_keys": []}}


def build_repair_plan(context: dict[str, Any], *, parent_condition_asset_id: str) -> RepairPlan:
    """Return a complete, child-adapted plan or reject the record before writes."""
    content = context.get("normalized_content")
    if not isinstance(content, dict) or content.get("format") != "teacherhelper-normalized" or content.get("schema_version") != 3:
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    ab, sine = _values(str(condition.get("html") or ""))
    result = ab * sine
    answer = _answer(result)
    transformations: list[dict[str, Any]] = []
    asset = _asset(content, parent_condition_asset_id)
    if asset is not None:
        transformations.append(asset)
    solution = _section(content, "solution")
    desired = _solution(ab, sine, result, operation="rewrite" if solution is not None else "add")
    if solution is None or str(solution.get("html") or "") != desired["value"]["html"]:
        transformations.append(desired)
    answer_section = _section(content, "answer")
    expected_answer = f'<p><span data-effect="spaced">{answer}</span></p>'
    if answer_section is None or str(answer_section.get("html") or "") != expected_answer:
        transformations.append({"transformation_target_id": "section:answer:1", "operation": "rewrite",
                                "value": {"title": "Ответ", "html": expected_answer, "asset_keys": []}})
    return RepairPlan(answer=answer, transformations=tuple(transformations))
