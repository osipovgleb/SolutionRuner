"""Strict area-ratio repair for source group 665285."""

from __future__ import annotations

from fractions import Fraction
from html import unescape
import re
from typing import Any

from ...triangles.right.planner import RepairPlan, RightTrianglePlanError


RULE = "parallelogram-665285-midpoint-trapezoid-area"


def _section(content: dict[str, Any], key: str) -> dict[str, Any] | None:
    found = [
        section
        for section in content.get("sections", [])
        if isinstance(section, dict) and section.get("key") == key
    ]
    if len(found) > 1:
        raise RightTrianglePlanError(f"multiple {key} sections")
    return found[0] if found else None


def _visible(html: str) -> str:
    return re.sub(
        r"\s+", " ", re.sub(r"<[^>]+>", " ", unescape(html))
    ).replace("\u00ad", "").strip()


def _area(html: str) -> int:
    text = _visible(html)
    required = (
        "Площадь параллелограмма ABCD равна",
        "Точка E — середина стороны AD",
        "Найдите площадь трапеции BCDE",
    )
    if any(part not in text for part in required):
        raise RightTrianglePlanError("condition is outside frozen group-665285 grammar")
    match = re.search(r"Площадь параллелограмма ABCD\s+равна\s*(\d+)", text)
    if match is None:
        raise RightTrianglePlanError("condition must state an integer parallelogram area")
    area = int(match.group(1))
    if area <= 0:
        raise RightTrianglePlanError("area must be positive")
    return area


def _decimal(value: Fraction) -> tuple[str, str]:
    """Return canonical answer text and inline-LaTeX decimal for quarter units."""

    if value.denominator == 1:
        rendered = str(value.numerator)
        return rendered, rendered
    if value.denominator == 2:
        whole, remainder = divmod(value.numerator, 2)
        if remainder == 1:
            return f"{whole},5", f"{whole}{{,}}5"
    if value.denominator == 4:
        whole, remainder = divmod(value.numerator, 4)
        if remainder in {1, 3}:
            suffix = "25" if remainder == 1 else "75"
            return f"{whole},{suffix}", f"{whole}{{,}}{suffix}"
    raise RightTrianglePlanError("area ratio is not a terminating quarter decimal")


def _asset(content: dict[str, Any], parent_asset_id: str) -> dict[str, Any] | None:
    images = [
        asset
        for asset in content.get("assets", [])
        if isinstance(asset, dict) and asset.get("kind") == "ordinary_image"
    ]
    target = [asset for asset in images if asset.get("asset_key") == "image_1"]
    if not target:
        return {
            "transformation_target_id": "asset:image_1",
            "operation": "add",
            "value": {
                "parent_target_id": "section:condition:1",
                "position": 0,
                "asset_key": "image_1",
                "asset_id": parent_asset_id,
                "url": f"/assets/{parent_asset_id}",
                "kind": "ordinary_image",
                "alt": "",
            },
        }
    if len(images) != 1 or len(target) != 1 or target[0].get("asset_id") != parent_asset_id:
        raise RightTrianglePlanError("foreign or ambiguous condition image")
    return None


def build_repair_plan(
    context: dict[str, Any], *, parent_condition_asset_id: str
) -> RepairPlan:
    content = context.get("normalized_content")
    if not isinstance(content, dict) or (
        content.get("format") != "teacherhelper-normalized"
        or content.get("schema_version") != 3
    ):
        raise RightTrianglePlanError("schema-v3 Normalized content is required")
    condition = _section(content, "condition")
    if condition is None:
        raise RightTrianglePlanError("condition section is required")
    area = _area(str(condition.get("html") or ""))
    answer, result = _decimal(Fraction(3 * area, 4))
    html = (
        f'<section data-content-kind="solution" data-content-rule="{RULE}" data-solution-title="Решение">'
        r'<p>Точка <span data-inline-latex="E"></span> — середина стороны <span data-inline-latex="AD"></span>, поэтому <span data-inline-latex="ED=\frac{1}{2}AD"></span>. В параллелограмме <span data-inline-latex="BC=AD"></span>:</p>'
        r'<center><p><span data-inline-latex="ED+BC=\frac{1}{2}AD+AD=\frac{3}{2}AD"></span>.</p></center>'
        r'<p>Выразим площадь трапеции через высоту <span data-inline-latex="h"></span> параллелограмма:</p>'
        r'<center><p><span data-inline-latex="S_{BCDE}=\frac{ED+BC}{2}\cdot h=\frac{\frac{3}{2}AD}{2}\cdot h=\frac{3}{4}AD\cdot h"></span>.</p></center>'
        r'<p>Так как <span data-inline-latex="S_{ABCD}=AD\cdot h"></span>, подставим данную площадь:</p>'
        fr'<center><p><span data-inline-latex="S_{{BCDE}}=\frac{{3}}{{4}}\cdot {area}={result}"></span>.</p></center>'
        '</section>'
    )
    transformations: list[dict[str, Any]] = []
    asset = _asset(content, parent_condition_asset_id)
    if asset is not None:
        transformations.append(asset)
    solution = _section(content, "solution")
    if solution is None or str(solution.get("html") or "") != html:
        transformations.append(
            {
                "transformation_target_id": "section:solution",
                "operation": "rewrite" if solution else "add",
                "value": {"title": "Решение", "html": html, "asset_keys": []},
            }
        )
    answer_html = f'<p><span data-effect="spaced">{answer}</span></p>'
    current_answer = _section(content, "answer")
    if current_answer is None or str(current_answer.get("html") or "") != answer_html:
        transformations.append(
            {
                "transformation_target_id": "section:answer:1",
                "operation": "rewrite",
                "value": {"title": "Ответ", "html": answer_html, "asset_keys": []},
            }
        )
    return RepairPlan(answer=answer, transformations=tuple(transformations))
