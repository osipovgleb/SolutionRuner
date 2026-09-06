"""Audited group 27591: area from two positive integer sides and included 30°."""

from fractions import Fraction
import re
import unicodedata
from typing import Any

from bs4 import BeautifulSoup

from ..isosceles.planner import (
    _asset_transformation,
    _formula_text,
    _normalized_content,
    _section,
    _section_transformation,
)
from ..right.planner import RepairPlan, RightTrianglePlanError

RULE = "general-triangle-27591-area-sas-30"
PARENT_PROBLEM_ID = "79ac61c1-1e29-4010-b3a5-22a628bb98d6"
PARENT_ASSET_ID = "4e20eaee-c328-4838-a749-0e6c1343eb60"
ASSET_URL = f"/assets/{PARENT_ASSET_ID}"
CONDITION = re.compile(
    r"Найдите площадь треугольника, две стороны которого равны "
    r"([1-9][0-9]{0,5}) и ([1-9][0-9]{0,5}), а угол между ними равен 30°\s*\."
)


def _text(html: str, *, condition: bool = False) -> str:
    """Accept only audited text markup; restore the one supported angle formula."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(True):
        if tag.name not in {"p", "span", "center", "img"}:
            raise RightTrianglePlanError("unsupported input markup")
        allowed = {"data-inline-latex", "data-effect"} if tag.name == "span" else set()
        if tag.name == "img" and condition:
            allowed = {"alt", "src", "data-asset-id", "data-asset-key",
                       "data-transformation-target-id"}
        if set(tag.attrs) - allowed:
            raise RightTrianglePlanError("unsupported input attributes")
        if tag.name == "img" and not condition:
            raise RightTrianglePlanError("unexpected answer image")
    for tag in soup.select("[data-inline-latex]"):
        if not condition or tag["data-inline-latex"] != r"30^{\circ}" or tag.get_text().strip():
            raise RightTrianglePlanError("unsupported or ambiguous formula")
        tag.replace_with("30°")
    text = unicodedata.normalize("NFKC", soup.get_text()).replace("\u00ad", "")
    return " ".join(text.split())


def _validate_assets(content: dict[str, Any], condition: dict[str, Any]) -> bool:
    """Only an absent diagram or the exact audited condition diagram is allowed."""
    assets = content.get("assets")
    if not isinstance(assets, list):
        raise RightTrianglePlanError("assets must be a list")
    images = BeautifulSoup(condition["html"], "html.parser").find_all("img")
    for section in content["sections"]:
        if section is not condition and (section.get("asset_keys") or
                BeautifulSoup(str(section.get("html") or ""), "html.parser").find("img")):
            raise RightTrianglePlanError("diagram must occur only in condition")
    if not assets and not images and condition.get("asset_keys", []) == []:
        return False
    if len(assets) != 1 or len(images) != 1 or condition.get("asset_keys") != ["image_1"]:
        raise RightTrianglePlanError("ambiguous condition assets")
    expected = {"asset_key": "image_1", "asset_id": PARENT_ASSET_ID,
                "url": ASSET_URL, "kind": "ordinary_image", "alt": ""}
    if any(assets[0].get(k) != v for k, v in expected.items()):
        raise RightTrianglePlanError("unrecognized condition diagram")
    image = images[0]
    if (image.get("data-transformation-target-id", "asset:image_1") != "asset:image_1"
            or assets[0].get("transformation_target_id", "asset:image_1") != "asset:image_1"):
        raise RightTrianglePlanError("condition asset target drifted")
    if any(image.get(k) != v for k, v in {
        "data-asset-key": "image_1", "data-asset-id": PARENT_ASSET_ID,
        "src": ASSET_URL, "alt": "",
    }.items()):
        raise RightTrianglePlanError("condition image reference drifted")
    return True


def build_repair_plan(context: dict[str, Any], *, parent_condition_asset_id: str, parent_solution_html: str = "") -> RepairPlan:
    """Compute from the condition, then repair stored answer and proof independently."""
    if parent_condition_asset_id != PARENT_ASSET_ID:
        raise RightTrianglePlanError("audited parent asset changed")
    content = _normalized_content(context)
    condition = _section(content, "condition")
    answer_section = _section(content, "answer")
    solution = _section(content, "solution")
    for section in (condition, answer_section, solution):
        if section is not None:
            key = section["key"]
            if (section.get("section_id") != f"{key}:1" or
                    section.get("transformation_target_id", f"section:{key}:1")
                    != f"section:{key}:1"):
                raise RightTrianglePlanError("noncanonical section identity")
    if condition is None or condition.get("section_id") != "condition:1":
        raise RightTrianglePlanError("canonical condition is required")
    match = CONDITION.fullmatch(_text(condition["html"], condition=True))
    if match is None:
        raise RightTrianglePlanError("unsupported group 27591 condition")
    a, b = map(int, match.groups())
    area = Fraction(a * b, 4)
    try:
        stored = _text(answer_section.get("html") or "") if answer_section else ""
        answer_matches = bool(re.fullmatch(r"[0-9]+(?:[,.][0-9]+)?", stored)) and (
            Fraction(stored.replace(",", ".")) == area
        )
    except (ValueError, TypeError):
        answer_matches = False
    # Integer sides imply quarters, so no floating-point formatting or tolerance.
    whole, remainder = divmod(a * b, 4)
    answer = str(whole) + ("", ",25", ",5", ",75")[remainder]
    has_image = _validate_assets(content, condition)
    changes = []
    if not has_image:
        changes.append(_asset_transformation(PARENT_ASSET_ID))
    formula = (
        rf"S=\frac{{1}}{{2}}\cdot {a}\cdot {b}\cdot \sin 30^{{\circ}}="
        rf"\frac{{1}}{{2}}\cdot {a}\cdot {b}\cdot \frac{{1}}{{2}}="
        + answer.replace(",", "{,}")
    )
    html = (
        "<p>Площадь треугольника равна половине произведения длин его сторон "
        "на синус угла между ними. Следовательно,</p><center><p>"
        f'<span data-inline-latex="{formula}"></span>.</p></center>'
    )
    # Preserve the audited proof (including source soft hyphens/spacing).
    # Unknown or contradictory proof text is replaced with the computed proof.
    existing_proof = _formula_text(str(solution.get("html") or "")) if solution else ""
    proof_soup = BeautifulSoup(str(solution.get("html") or "") if solution else "", "html.parser")
    proof_markup_valid = all(
        tag.name in {"p", "center", "span"}
        and not (set(tag.attrs) - ({"data-inline-latex"} if tag.name == "span" else set()))
        for tag in proof_soup.find_all(True)
    )
    if (not proof_markup_valid or
            re.sub(r"\s+", "", existing_proof) != re.sub(r"\s+", "", _formula_text(html))):
        changes.append(_section_transformation(solution, "solution", "Решение", html))
    if not answer_matches:
        changes.append(_section_transformation(
            answer_section, "answer", "Ответ",
            f'<p><span data-effect="spaced">{answer}</span></p>',
        ))
    return RepairPlan(answer=answer, transformations=tuple(changes))
