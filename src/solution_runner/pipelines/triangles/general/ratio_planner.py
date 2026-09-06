"""Strict angle-ratio repair rule for general-triangle group 27752."""

from __future__ import annotations

from fractions import Fraction
import re
from typing import Any

from bs4 import BeautifulSoup

from ..isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from ..right.planner import RepairPlan, RightTrianglePlanError


RULE = "general-triangle-27752-angle-ratio"
CONDITION_ASSET_ID = "74d09078-6b65-4331-ab6f-2b3c7e7dbe84"
CONDITION_ASSET_SHA256 = (
    "074c1cd588d00ba7fccad7e06e301a5d90601b65486d1b9710473666dde1fb93"
)
CONDITION_ASSET_ALT = "Схематический треугольник, рисунок не в масштабе."

_CONDITION = re.compile(
    r"Углы треугольника относятся как "
    r"(?P<a>[1-9]\d{0,5})\s*(?::|\\colon)\s*"
    r"(?P<b>[1-9]\d{0,5})\s*(?::|\\colon)\s*"
    r"(?P<c>[1-9]\d{0,5})\s*\. "
    r"Найдите меньший из них\. Ответ дайте в градусах\.",
    re.IGNORECASE,
)


def _condition_text(condition_html: str) -> str:
    """Restore one optional inline ratio and return normalized visible text."""

    soup = BeautifulSoup(condition_html, "html.parser")
    image_wrappers = soup.find_all("center")
    if len(image_wrappers) > 1:
        raise RightTrianglePlanError("condition contains duplicate image markup")
    for wrapper in image_wrappers:
        children = [item for item in wrapper.children if getattr(item, "name", None)]
        if len(children) != 1 or children[0].name != "img":
            raise RightTrianglePlanError("condition contains unsupported centered markup")
        image = children[0]
        if (
            image.get("data-asset-key") != "image_1"
            or image.get("data-asset-id") != CONDITION_ASSET_ID
            or image.get("src") != f"/assets/{CONDITION_ASSET_ID}"
            or image.get("alt") != CONDITION_ASSET_ALT
            or set(image.attrs)
            not in (
                {"alt", "data-asset-id", "data-asset-key", "src"},
                {
                    "alt",
                    "data-asset-id",
                    "data-asset-key",
                    "data-transformation-target-id",
                    "src",
                },
            )
            or image.get("data-transformation-target-id") not in (None, "asset:image_1")
        ):
            raise RightTrianglePlanError("condition contains foreign image markup")
        wrapper.decompose()
    if any(tag.name not in {"p", "span"} for tag in soup.find_all(True)):
        raise RightTrianglePlanError("condition contains unsupported markup")
    for tag in soup.find_all(True):
        allowed = set() if tag.name == "p" else {"data-inline-latex"}
        if set(tag.attrs) != allowed:
            raise RightTrianglePlanError("condition contains unsupported attributes")
    formulas = soup.find_all(attrs={"data-inline-latex": True})
    if len(formulas) > 1:
        raise RightTrianglePlanError("condition must contain at most one inline ratio")
    for formula in formulas:
        if formula.get_text("", strip=True):
            raise RightTrianglePlanError("inline ratio contains conflicting fallback text")
        raw = str(formula.get("data-inline-latex") or "")
        if re.fullmatch(
            r"[1-9]\d{0,5}\s*\\colon\s*[1-9]\d{0,5}\s*\\colon\s*[1-9]\d{0,5}",
            raw,
        ) is None:
            raise RightTrianglePlanError("inline ratio has an unsupported form")
        formula.replace_with(raw)
    return " ".join(
        soup.get_text(" ", strip=True)
        .replace("\u00ad", "")
        .replace("\u202f", " ")
        .split()
    )


def _parse_ratio(condition_html: str) -> tuple[int, int, int]:
    text = _condition_text(condition_html)
    match = _CONDITION.fullmatch(text)
    if match is None:
        raise RightTrianglePlanError("condition does not match the registered angle-ratio rule")
    return tuple(int(match.group(name)) for name in ("a", "b", "c"))


def _term(coefficient: int) -> str:
    return "x" if coefficient == 1 else f"{coefficient}x"


def _solution_html(ratio: tuple[int, int, int]) -> tuple[int, str]:
    total = sum(ratio)
    unit = Fraction(180, total)
    answer = min(ratio) * unit
    if unit.denominator != 1 or answer.denominator != 1:
        raise RightTrianglePlanError("angle-ratio rule requires integral degree values")
    unit_value = unit.numerator
    answer_value = answer.numerator
    terms = tuple(_term(value) for value in ratio)
    sum_formula = "+".join(terms)
    first_row = (
        rf"{sum_formula}=180^{{\circ}}\iff "
        rf"{total}x=180^{{\circ}}\iff x={unit_value}^{{\circ}}"
    )
    least = min(ratio)
    last_row = (
        rf"{least}x={least}\cdot{unit_value}^{{\circ}}={answer_value}^{{\circ}}"
        if least != 1
        else rf"x={unit_value}^{{\circ}}"
    )
    html = (
        f"<p>Пусть углы треугольника равны "
        f'<span data-inline-latex="{terms[0]}"></span>, '
        f'<span data-inline-latex="{terms[1]}"></span> и '
        f'<span data-inline-latex="{terms[2]}"></span>. Тогда</p>'
        f'<center><p><span data-inline-latex="{first_row}"></span>.</p></center>'
        "<p>Следовательно,</p>"
        f'<center><p><span data-inline-latex="{last_row}"></span>.</p></center>'
    )
    return answer_value, html


def _answer_matches(section: dict[str, Any] | None, expected: int) -> bool:
    if section is None:
        return False
    current = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        " ", strip=True
    )
    try:
        return Fraction(current.replace(",", ".")) == expected
    except (ValueError, ZeroDivisionError):
        return False


def _asset_transformation() -> dict[str, Any]:
    html = (
        f'<center><img alt="{CONDITION_ASSET_ALT}" '
        f'data-asset-id="{CONDITION_ASSET_ID}" data-asset-key="image_1" '
        f'src="/assets/{CONDITION_ASSET_ID}"/></center>'
    )
    return {
        "transformation_target_id": "asset:image_1",
        "operation": "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": "image_1",
            "asset_id": CONDITION_ASSET_ID,
            "url": f"/assets/{CONDITION_ASSET_ID}",
            "kind": "ordinary_image",
            "alt": CONDITION_ASSET_ALT,
            "html": html,
        },
    }


def _condition_has_asset(content: dict[str, Any], condition: dict[str, Any]) -> bool:
    assets = content.get("assets")
    if not isinstance(assets, list):
        raise RightTrianglePlanError("normalized assets must be a list")
    ordinary = [item for item in assets if isinstance(item, dict)]
    if not ordinary:
        if condition.get("asset_keys") not in (None, []):
            raise RightTrianglePlanError("condition asset references are unresolved")
        return False
    if len(ordinary) != 1:
        raise RightTrianglePlanError("condition contains foreign or duplicate assets")
    asset = ordinary[0]
    if (
        asset.get("asset_key") != "image_1"
        or asset.get("kind") != "ordinary_image"
        or asset.get("asset_id") != CONDITION_ASSET_ID
        or asset.get("url") != f"/assets/{CONDITION_ASSET_ID}"
        or asset.get("alt") != CONDITION_ASSET_ALT
    ):
        raise RightTrianglePlanError("condition contains a foreign asset")
    if tuple(condition.get("asset_keys") or ()) != ("image_1",):
        raise RightTrianglePlanError("condition does not own the registered asset")
    for section in content.get("sections", []):
        if section is not condition and "image_1" in tuple(section.get("asset_keys") or ()):
            raise RightTrianglePlanError("registered asset is attached outside the condition")
    return True


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
    parent_solution_html: str = "",
) -> RepairPlan:
    """Build an exact solution, answer, and shared-condition-asset repair."""

    del parent_solution_html
    if parent_condition_asset_id != CONDITION_ASSET_ID:
        raise RightTrianglePlanError("registered group condition asset changed")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    ratio = _parse_ratio(str(condition.get("html") or ""))
    answer, solution_html = _solution_html(ratio)
    changes: list[dict[str, Any]] = []

    answer_section = _section(content, "answer")
    if not _answer_matches(answer_section, answer):
        changes.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )

    solution = _section(content, "solution")
    if solution is None or str(solution.get("html") or "") != solution_html:
        changes.append(
            _section_transformation(
                solution,
                "solution",
                "Решение",
                solution_html,
            )
        )

    if not _condition_has_asset(content, condition):
        changes.append(_asset_transformation())
    return RepairPlan(answer=str(answer), transformations=tuple(changes))
