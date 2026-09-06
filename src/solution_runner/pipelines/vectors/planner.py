"""Strict repair planner for vector group 27718."""

from __future__ import annotations

from fractions import Fraction
from html import escape
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


RULE = "vector-27718-rhombus-diagonal-difference"
PARENT_PROBLEM_ID = "26128435-2125-4369-87db-a9e21e89520e"
CONDITION_ASSET_ID = "04298a22-5a29-4405-bdab-329a35c976f7"
CONDITION_ASSET_SHA256 = (
    "bbbdee49f44a34050b9a247b3fec3d3a0a386c4992c6a11b56b2ef7a3839c83a"
)
CONDITION_ASSET_ALT = ""

_RASTER_CONTENT_TYPES = frozenset({"image/jpeg", "image/png"})
_CONDITION = re.compile(
    r"Диагонали ромба ABCD пересекаются в точке O и равны "
    r"(?P<first>[1-9]\d{0,5}) и (?P<second>[1-9]\d{0,5})\. "
    r"Найдите длину вектора "
    r"\\overrightarrow\{AO\}-\\overrightarrow\{BO\}\."
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


def _asset_html(
    asset_id: str,
    alt: str,
    *,
    transformation_target: bool = False,
) -> str:
    target = (
        ' data-transformation-target-id="asset:image_1"'
        if transformation_target
        else ""
    )
    return (
        f'<img alt="{escape(alt, quote=True)}" '
        f'data-asset-id="{asset_id}" data-asset-key="image_1"'
        f'{target} src="/assets/{asset_id}"/>'
    )


def _asset_transformation(
    asset_id: str,
    alt: str,
    *,
    replace: bool,
) -> dict[str, Any]:
    return {
        "transformation_target_id": "asset:image_1",
        "operation": "rewrite" if replace else "add",
        "value": {
            "parent_target_id": "section:condition:1",
            "position": 0,
            "asset_key": "image_1",
            "asset_id": asset_id,
            "url": f"/assets/{asset_id}",
            "kind": "ordinary_image",
            "alt": alt,
            "html": _asset_html(asset_id, alt),
        },
    }


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
            "var": {"data-math-identifier"},
            "span": {"data-inline-latex"},
        }.get(tag.name)
        if allowed is None or set(tag.attrs) != allowed:
            raise RightTrianglePlanError("condition contains unsupported markup")
    variables = soup.find_all("var")
    if [tag.get("data-math-identifier") for tag in variables] != ["ABCD", "O"]:
        raise RightTrianglePlanError("condition variables do not match the registered form")
    for tag, expected in zip(variables, ("ABCD", "O"), strict=True):
        if tag.get_text("", strip=True) != expected:
            raise RightTrianglePlanError("condition variable fallback is inconsistent")
        tag.replace_with(expected)
    formulas = soup.find_all("span")
    expected_formula = r"\overrightarrow{AO}-\overrightarrow{BO}"
    if len(formulas) != 1 or formulas[0].get("data-inline-latex") != expected_formula:
        raise RightTrianglePlanError("condition vector expression is unsupported")
    if formulas[0].get_text("", strip=True):
        raise RightTrianglePlanError("condition vector formula has conflicting fallback")
    formulas[0].replace_with(expected_formula)
    text = soup.get_text(" ", strip=True).replace("\u00ad", "").replace("\u202f", " ")
    return re.sub(r"\s+([.])", r"\1", " ".join(text.split()))


def _condition_asset_state(
    content: dict[str, Any],
    condition: dict[str, Any],
    *,
    current_asset_content_type: str | None,
    registered_asset_id: str,
    registered_alt: str,
) -> tuple[str | None, bool]:
    assets = content.get("assets")
    if not isinstance(assets, list):
        raise RightTrianglePlanError("normalized assets must be a list")
    ordinary = [item for item in assets if isinstance(item, dict)]
    if len(ordinary) > 1:
        raise RightTrianglePlanError("condition contains duplicate or foreign assets")
    for section in content.get("sections", []):
        if section is not condition and tuple(section.get("asset_keys") or ()):
            raise RightTrianglePlanError("condition image is referenced by another section")
    if not ordinary:
        if tuple(condition.get("asset_keys") or ()):
            raise RightTrianglePlanError("condition has an unresolved asset reference")
        if BeautifulSoup(str(condition.get("html") or ""), "html.parser").find("img"):
            raise RightTrianglePlanError("condition has unresolved image markup")
        return None, False

    asset = ordinary[0]
    asset_id = str(asset.get("asset_id") or "")
    if (
        not asset_id
        or asset.get("asset_key") != "image_1"
        or asset.get("kind") != "ordinary_image"
        or asset.get("url") != f"/assets/{asset_id}"
        or asset.get("transformation_target_id") not in (None, "asset:image_1")
        or tuple(condition.get("asset_keys") or ()) != ("image_1",)
    ):
        raise RightTrianglePlanError("condition asset identity is ambiguous")
    content_type = str(current_asset_content_type or "").split(";", 1)[0].lower()
    if asset_id == registered_asset_id:
        if content_type != "image/svg+xml" or asset.get("alt") != registered_alt:
            raise RightTrianglePlanError("registered condition SVG metadata drifted")
        return asset_id, True
    if content_type not in _RASTER_CONTENT_TYPES:
        raise RightTrianglePlanError("foreign condition asset is not an approved raster")
    if str(asset.get("alt") or ""):
        raise RightTrianglePlanError("raster condition asset has unexpected alt text")
    return asset_id, False


def _half_latex(value: int) -> str:
    if value % 2 == 0:
        return str(value // 2)
    return f"{value // 2}{{,}}5"


def _answer_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    if value.denominator == 2:
        return f"{value.numerator // 2},5"
    raise RightTrianglePlanError("computed answer has an unsupported exact form")


def _answer_matches(section: dict[str, Any] | None, expected: Fraction) -> bool:
    if section is None:
        return False
    text = BeautifulSoup(str(section.get("html") or ""), "html.parser").get_text(
        " ", strip=True
    )
    try:
        return bool(re.fullmatch(r"\d+(?:[,.]\d+)?", text)) and Fraction(
            text.replace(",", ".")
        ) == expected
    except (ValueError, ZeroDivisionError):
        return False


def _solution_html(first: int, second: int, answer: str) -> str:
    first_half = _half_latex(first)
    second_half = _half_latex(second)
    formula = (
        rf"AB=\sqrt{{{second_half}^2+{first_half}^2}}="
        + answer.replace(",", "{,}")
    )
    return (
        '<p>Раз­ность век­то­ров '
        '<span data-inline-latex="\\overrightarrow{AO}"></span> и '
        '<span data-inline-latex="\\overrightarrow{BO}"></span> равна век­то­ру '
        '<span data-inline-latex="\\overrightarrow{AB}"></span>. Диа­го­на­ли '
        'ромба пе­ре­се­ка­ют­ся под пря­мым углом и точ­кой пе­ре­се­че­ния '
        'де­лят­ся по­по­лам. Тогда век­тор '
        '<span data-inline-latex="\\overrightarrow{AB}"></span> яв­ля­ет­ся '
        'ги­по­те­ну­зой в пря­мо­уголь­ном тре­уголь­ни­ке. По тео­ре­ме '
        'Пи­фа­го­ра по­лу­ча­ем, что '
        f'<span data-inline-latex="{formula}"></span></p>'
    )


def build_repair_plan(
    context: dict[str, Any],
    *,
    parent_condition_asset_id: str,
    parent_solution_html: str = "",
    current_asset_content_type: str | None = None,
) -> RepairPlan:
    """Compute the vector length and converge solution, answer, and SVG asset."""

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
        raise RightTrianglePlanError("condition does not match vector group 27718")
    first, second = (int(match.group(name)) for name in ("first", "second"))
    diagonal_square_sum = first * first + second * second
    diagonal_hypotenuse = math.isqrt(diagonal_square_sum)
    if diagonal_hypotenuse * diagonal_hypotenuse != diagonal_square_sum:
        raise RightTrianglePlanError("diagonal values do not produce a supported exact answer")
    exact_answer = Fraction(diagonal_hypotenuse, 2)
    answer = _answer_text(exact_answer)
    expected_solution = _solution_html(first, second, answer)

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
    if not _answer_matches(answer_section, exact_answer):
        changes.append(
            _section_transformation(
                answer_section,
                "answer",
                "Ответ",
                f'<p><span data-effect="spaced">{answer}</span></p>',
            )
        )
    return RepairPlan(answer=answer, transformations=tuple(changes))
