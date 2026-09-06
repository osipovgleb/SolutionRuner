"""Strict repair planner for vector group 27708."""

from __future__ import annotations

import math
import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from ..triangles.isosceles.planner import (
    _normalized_content,
    _section,
    _section_transformation,
)
from ..triangles.right.planner import RepairPlan, RightTrianglePlanError
from .planner import _asset_transformation, _condition_asset_state


RULE = "vector-27708-rectangle-vector-sum-length"
PARENT_PROBLEM_ID = "a5911e86-63f8-4612-93d9-8751707fe3aa"
CONDITION_ASSET_ID = "83e55258-af58-415f-8b8b-0dd18e7c596c"
CONDITION_ASSET_SHA256 = (
    "b6985c2e9d8332c85a9c97972bd11ff6b511619b214b465694d3f42c4bec6e18"
)
CONDITION_ASSET_ALT = ""

_CONDITION = re.compile(
    r"Две стороны прямоугольника ABCD равны (?P<a>[1-9]\d{0,5}) и "
    r"(?P<b>[1-9]\d{0,5})\. Найдите длину суммы векторов "
    r"\\overrightarrow\{AB\} и \\overrightarrow\{AD\}\."
)


def _canonical_section(section: dict[str, Any] | None, key: str) -> None:
    if section is None:
        return
    if (
        section.get("section_id") != f"{key}:1"
        or section.get("transformation_target_id", f"section:{key}:1")
        != f"section:{key}:1"
    ):
        raise RightTrianglePlanError("noncanonical section identity")


def _condition_text(
    condition: dict[str, Any],
    *,
    expected_current_asset_id: str | None,
) -> str:
    soup = BeautifulSoup(str(condition.get("html") or ""), "html.parser")
    images = soup.find_all("img")
    if len(images) > 1:
        raise RightTrianglePlanError("condition contains duplicate image markup")
    if images:
        image = images[0]
        if (
            expected_current_asset_id is None
            or image.get("data-asset-key") != "image_1"
            or image.get("data-asset-id") != expected_current_asset_id
            or image.get("src") != f"/assets/{expected_current_asset_id}"
            or image.get("data-transformation-target-id")
            not in (None, "asset:image_1")
            or set(image.attrs)
            - {
                "alt",
                "data-asset-id",
                "data-asset-key",
                "data-transformation-target-id",
                "src",
            }
        ):
            raise RightTrianglePlanError("condition image markup is foreign")
        wrapper = image.parent
        image.decompose()
        if (
            isinstance(wrapper, Tag)
            and wrapper.name in {"center", "figure"}
            and not wrapper.get_text(strip=True)
        ):
            wrapper.decompose()

    for tag in soup.find_all(True):
        allowed = {
            "p": set(),
            "i": set(),
            "span": {"data-inline-latex"},
        }.get(tag.name)
        if allowed is None or set(tag.attrs) != allowed:
            raise RightTrianglePlanError("condition contains unsupported markup")
    italics = soup.find_all("i")
    if len(italics) != 1 or italics[0].get_text("", strip=True) != "ABCD":
        raise RightTrianglePlanError("condition rectangle name is unsupported")
    italics[0].replace_with("ABCD")
    formulas = soup.find_all("span")
    expected = (r"\overrightarrow{AB}", r"\overrightarrow{AD}")
    if tuple(tag.get("data-inline-latex") for tag in formulas) != expected:
        raise RightTrianglePlanError("condition vector expressions are unsupported")
    if any(tag.get_text("", strip=True) for tag in formulas):
        raise RightTrianglePlanError("condition vector formula has conflicting fallback")
    for tag, formula in zip(formulas, expected, strict=True):
        tag.replace_with(formula)
    text = soup.get_text(" ", strip=True).replace("\u00ad", "").replace("\u202f", " ")
    return re.sub(r"\s+([.])", r"\1", " ".join(text.split()))


def _answer_matches(section: dict[str, Any] | None, answer: int) -> bool:
    if section is None:
        return False
    text = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        " ", strip=True
    )
    return bool(re.fullmatch(r"\d+", text)) and int(text) == answer


def _solution_html(a: int, b: int, answer: int) -> str:
    square_sum = a * a + b * b
    formula = rf"AC=\sqrt{{{a}^{{2}}+{b}^{{2}}}}=\sqrt{{{square_sum}}}={answer}"
    return (
        '<p>Сумма век­то­ров  '
        '<span data-inline-latex="\\overrightarrow{AB}"></span> и  '
        '<span data-inline-latex="\\overrightarrow{AD}"></span> равна век­то­ру  '
        '<span data-inline-latex="\\overrightarrow{AC}"></span>. Век­тор  '
        '<span data-inline-latex="\\overrightarrow{AC}"></span> делит '
        'пря­мо­уголь­ник на два пря­мо­уголь­ных тре­уголь­ни­ка. '
        'Сле­до­ва­тель­но, по тео­ре­ме Пи­фа­го­ра по­лу­ча­ем:</p>'
        '<center><p> '
        f'<span data-inline-latex="{formula}"></span>.</p></center>'
    )


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    """Compute the vector-sum length and converge answer, proof, and SVG."""

    del parent_solution_html
    if parent_condition_asset_id != CONDITION_ASSET_ID:
        raise RightTrianglePlanError("registered group condition asset changed")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution = _section(content, "solution")
    for key, section in (
        ("condition", condition),
        ("answer", answer_section),
        ("solution", solution),
    ):
        _canonical_section(section, key)
    if condition is None:
        raise RightTrianglePlanError("canonical condition is required")

    current_asset_id, has_registered_svg = _condition_asset_state(
        content,
        condition,
        current_asset_content_type=current_asset_content_type,
        registered_asset_id=CONDITION_ASSET_ID,
        registered_alt=CONDITION_ASSET_ALT,
    )
    match = _CONDITION.fullmatch(
        _condition_text(condition, expected_current_asset_id=current_asset_id)
    )
    if match is None:
        raise RightTrianglePlanError("condition does not match vector group 27708")
    a, b = (int(match.group(name)) for name in ("a", "b"))
    square_sum = a * a + b * b
    answer = math.isqrt(square_sum)
    if answer * answer != square_sum:
        raise RightTrianglePlanError("side lengths do not produce a supported exact answer")
    expected_solution = _solution_html(a, b, answer)

    changes: list[dict[str, Any]] = []
    if not has_registered_svg:
        changes.append(
            _asset_transformation(
                CONDITION_ASSET_ID,
                CONDITION_ASSET_ALT,
                replace=current_asset_id is not None,
            )
        )
    if solution is None or str(solution.get("html") or "") != expected_solution:
        changes.append(
            _section_transformation(
                solution, "solution", "Решение", expected_solution
            )
        )
    if not _answer_matches(answer_section, answer):
        changes.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=str(answer), transformations=tuple(changes))
